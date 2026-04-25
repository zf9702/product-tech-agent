"""
产品技术资料管理系统 - 主应用
FastAPI + SQLite + Fernet 加密
"""
import os
import io
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import (
    FastAPI, Depends, HTTPException, UploadFile, File,
    Form, Request, Query, status
)
from fastapi.responses import (
    HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse
)
from urllib.parse import quote
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from config import BASE_DIR, DATA_DIR, HOST, PORT, MAX_UPLOAD_SIZE_MB, ALLOWED_EXTENSIONS
from database import init_db, get_db, User, Document, Category, AccessLog, DocNumberRule, ProductSpec
from auth import (
    hash_password, verify_password, create_token,
    get_current_user, require_role
)
from encryption import encrypt_file, decrypt_file, delete_file
from office_convert import docx_to_pdf, get_office_type
from doc_parser import extract_text_from_bytes, init_fts, index_document, search_document_context, get_all_doc_content
from ai_engine import load_ai_config, save_ai_config, is_ai_available, ask_question, check_compliance

app = FastAPI(title="产品技术资料管理系统", version="1.1.0")

STATIC_DIR = BASE_DIR / "static"
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR.mkdir(exist_ok=True)
(STATIC_DIR / "css").mkdir(exist_ok=True)
(STATIC_DIR / "js").mkdir(exist_ok=True)
TEMPLATE_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


# ─── 启动事件 ─────────────────────────────────────
@app.on_event("startup")
def startup():
    init_db()
    from database import SessionLocal
    db = SessionLocal()
    try:
        # 创建默认管理员
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                display_name="系统管理员",
                password_hash=hash_password("admin123"),
                role="admin",
                department="管理部",
            )
            db.add(admin)
            db.commit()
            print("=" * 50)
            print("  系统已初始化")
            print("  默认管理员: admin / admin123")
            print("  请首次登录后立即修改密码！")
            print("=" * 50)

        # 初始化默认编号规则
        if db.query(DocNumberRule).count() == 0:
            default_rules = [
                DocNumberRule(type_code="TD", type_name="技术条件",
                              template="{product}-{code}-{year}-{seq}", seq_digits=3, sort_order=1),
                DocNumberRule(type_code="DW", type_name="图样",
                              template="{product}-{code}-{year}-{seq}", seq_digits=3, sort_order=2),
                DocNumberRule(type_code="JS", type_name="技术说明书",
                              template="{product}-{code}-{year}-{seq}", seq_digits=3, sort_order=3),
                DocNumberRule(type_code="JY", type_name="检验规程",
                              template="{product}-{code}-{year}-{seq}", seq_digits=3, sort_order=4),
                DocNumberRule(type_code="GY", type_name="工艺规程",
                              template="{product}-{code}-{year}-{seq}", seq_digits=3, sort_order=5),
                DocNumberRule(type_code="BZ", type_name="标准化审查报告",
                              template="{product}-{code}-{year}-{seq}", seq_digits=3, sort_order=6),
                DocNumberRule(type_code="YJ", type_name="研究/试验报告",
                              template="{product}-{code}-{year}-{seq}", seq_digits=3, sort_order=7),
                DocNumberRule(type_code="FA", type_name="方案/大纲",
                              template="{product}-{code}-{year}-{seq}", seq_digits=3, sort_order=8),
                DocNumberRule(type_code="BG", type_name="报告",
                              template="{product}-{code}-{year}-{seq}", seq_digits=3, sort_order=9),
                DocNumberRule(type_code="QT", type_name="其他",
                              template="{product}-{code}-{year}-{seq}", seq_digits=3, sort_order=99),
            ]
            db.add_all(default_rules)
            db.commit()
            print("  已初始化 10 个默认编号规则")

        # 初始化全文检索索引
        init_fts()
    finally:
        db.close()


# ═══════════════════════════════════════════════════
#  页面路由
# ═══════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    token = request.cookies.get("access_token")
    if token:
        return RedirectResponse("/dashboard", status_code=302)
    return RedirectResponse("/login", status_code=302)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {
            "request": request, "error": "用户名或密码错误",
        })
    if not user.is_active:
        return templates.TemplateResponse("login.html", {
            "request": request, "error": "账户已被禁用",
        })
    user.last_login = datetime.utcnow()
    db.commit()
    token = create_token(user.id, user.username, user.role)
    resp = RedirectResponse("/dashboard", status_code=302)
    resp.set_cookie("access_token", token, httponly=True, max_age=480*60)
    return resp


@app.get("/logout")
def logout():
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie("access_token")
    return resp


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc_count = db.query(Document).count()
    cat_count = db.query(Category).count()
    recent_docs = (
        db.query(Document).order_by(Document.created_at.desc()).limit(10).all()
    )
    return templates.TemplateResponse("dashboard.html", {
        "request": request, "user": user,
        "doc_count": doc_count, "cat_count": cat_count,
        "recent_docs": recent_docs,
    })


@app.get("/documents", response_class=HTMLResponse)
def document_list(
    request: Request,
    q: str = Query(""),
    category_id: Optional[int] = Query(None),
    product_model: str = Query(""),
    page: int = Query(1, ge=1),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Document)
    if q:
        query = query.filter(or_(
            Document.title.contains(q),
            Document.description.contains(q),
            Document.doc_number.contains(q),
        ))
    if category_id:
        query = query.filter(Document.category_id == category_id)
    if product_model:
        query = query.filter(Document.product_model.contains(product_model))

    per_page = 20
    total = query.count()
    docs = (
        query.order_by(Document.updated_at.desc())
        .offset((page - 1) * per_page).limit(per_page).all()
    )
    categories = db.query(Category).order_by(Category.name).all()

    return templates.TemplateResponse("documents.html", {
        "request": request, "user": user,
        "documents": docs, "categories": categories,
        "total": total, "page": page, "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page,
        "q": q, "selected_category": category_id,
        "product_model": product_model,
    })


@app.get("/upload", response_class=HTMLResponse)
def upload_page(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    categories = db.query(Category).order_by(Category.name).all()
    rules = db.query(DocNumberRule).order_by(DocNumberRule.sort_order).all()
    return templates.TemplateResponse("upload.html", {
        "request": request, "user": user,
        "categories": categories, "rules": rules,
    })


@app.get("/batch-upload", response_class=HTMLResponse)
def batch_upload_page(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    categories = db.query(Category).order_by(Category.name).all()
    rules = db.query(DocNumberRule).order_by(DocNumberRule.sort_order).all()
    return templates.TemplateResponse("batch_upload.html", {
        "request": request, "user": user,
        "categories": categories, "rules": rules,
    })


@app.post("/upload")
async def upload_submit(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(""),
    product_model: str = Form(""),
    doc_number: str = Form(""),
    doc_type_code: str = Form(""),
    version: str = Form("1.0"),
    category_id: Optional[int] = Form(None),
    new_category: str = Form(""),
    access_level: str = Form("public"),
    user: User = Depends(require_role("admin", "editor")),
    db: Session = Depends(get_db),
):
    # 如果填写了新分类名称，先创建分类
    if new_category.strip():
        existing = db.query(Category).filter(Category.name == new_category.strip()).first()
        if not existing:
            cat = Category(name=new_category.strip())
            db.add(cat)
            db.flush()
            category_id = cat.id
        else:
            category_id = existing.id

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的文件类型: {ext}")

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(400, f"文件大小超过 {MAX_UPLOAD_SIZE_MB}MB 限制")

    stored_name = f"{uuid.uuid4().hex}{ext}.enc"
    tmp_path = DATA_DIR / f"tmp_{uuid.uuid4().hex}"
    try:
        with open(tmp_path, "wb") as f:
            f.write(content)
        encrypt_file(str(tmp_path), stored_name)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    doc = Document(
        title=title, description=description,
        filename=file.filename, stored_name=stored_name,
        file_size=len(content), file_type=ext,
        product_model=product_model, doc_number=doc_number,
        doc_type_code=doc_type_code, version=version,
        category_id=category_id, access_level=access_level,
        uploaded_by=user.id,
    )
    db.add(doc)
    db.flush()  # 先写入数据库拿到 doc.id
    log = AccessLog(
        document_id=doc.id, user_id=user.id,
        action="upload", ip_address=request.client.host,
    )
    db.add(log)
    db.commit()

    # 自动提取文档内容并建立全文索引
    try:
        text = extract_text_from_bytes(content, ext)
        if text.strip():
            index_document(doc.id, doc.title, text, product_model, doc_number)
    except Exception:
        pass  # 索引失败不影响上传

    return RedirectResponse("/documents", status_code=302)


@app.get("/download/{doc_id}")
def download_document(
    doc_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "文档不存在")
    try:
        plaintext = decrypt_file(doc.stored_name)
    except Exception:
        raise HTTPException(404, "文件不存在或已损坏")
    log = AccessLog(
        document_id=doc.id, user_id=user.id,
        action="download", ip_address=request.client.host,
    )
    db.add(log)
    db.commit()
    return StreamingResponse(
        iter([plaintext]),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(doc.filename)}",
            "Content-Length": str(len(plaintext)),
        },
    )


# MIME类型映射
MIME_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".txt": "text/plain; charset=utf-8",
    ".md": "text/plain; charset=utf-8",
    ".csv": "text/csv; charset=utf-8",
    ".xml": "text/xml; charset=utf-8",
    ".json": "application/json",
    ".html": "text/html",
}


@app.get("/preview/{doc_id}", response_class=HTMLResponse)
def preview_page(
    doc_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """在线预览页面"""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "文档不存在")
    # 记录查看日志
    log = AccessLog(
        document_id=doc.id, user_id=user.id,
        action="view", ip_address=request.client.host,
    )
    db.add(log)
    db.commit()
    return templates.TemplateResponse("preview.html", {
        "request": request, "user": user, "doc": doc,
        "file_type": doc.file_type.lower() if doc.file_type else "",
    })


@app.get("/preview-file/{doc_id}")
def preview_file(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """返回解密后的文件内容（用于iframe/img预览）"""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "文档不存在")
    try:
        plaintext = decrypt_file(doc.stored_name)
    except Exception:
        raise HTTPException(404, "文件不存在或已损坏")

    ft = doc.file_type.lower() if doc.file_type else ""

    # .docx: 尝试用 WPS/Word 转 PDF 后预览
    if ft == ".docx":
        import tempfile
        tmp_docx = tempfile.NamedTemporaryFile(suffix=".docx", delete=False)
        tmp_docx.write(plaintext)
        tmp_docx.close()
        try:
            pdf_path = docx_to_pdf(tmp_docx.name, doc_id)
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    pdf_data = f.read()
                return StreamingResponse(
                    iter([pdf_data]),
                    media_type="application/pdf",
                    headers={"Content-Length": str(len(pdf_data))},
                )
        finally:
            try:
                os.unlink(tmp_docx.name)
            except:
                pass
        # 转换失败，回退到 mammoth.js 渲染（在 preview.html 中处理）
        raise HTTPException(422, "Office转换不可用")

    mime = MIME_TYPES.get(ft, "application/octet-stream")
    return StreamingResponse(
        iter([plaintext]),
        media_type=mime,
        headers={"Content-Length": str(len(plaintext))},
    )


@app.get("/document/{doc_id}", response_class=HTMLResponse)
def document_detail(
    doc_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "文档不存在")
    logs = (
        db.query(AccessLog).filter(AccessLog.document_id == doc_id)
        .order_by(AccessLog.timestamp.desc()).limit(50).all()
    )
    return templates.TemplateResponse("document_detail.html", {
        "request": request, "user": user, "doc": doc, "logs": logs,
    })


@app.post("/document/{doc_id}/delete")
def delete_document(
    doc_id: int,
    request: Request,
    user: User = Depends(require_role("admin", "editor")),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "文档不存在")
    delete_file(doc.stored_name)
    db.query(AccessLog).filter(AccessLog.document_id == doc_id).delete()
    db.delete(doc)
    db.commit()
    return RedirectResponse("/documents", status_code=302)


# ─── 自动生成编号 API ────────────────────────────
@app.get("/api/generate-number")
def api_generate_number(
    product_model: str = Query(..., description="产品型号"),
    type_code: str = Query(..., description="文件类型码"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """根据产品型号和文件类型自动生成下一个编号"""
    rule = db.query(DocNumberRule).filter(DocNumberRule.type_code == type_code).first()
    if not rule:
        return JSONResponse({"error": "未找到该文件类型的编号规则"}, status_code=400)

    now = datetime.utcnow()
    year = str(now.year)

    # 查找该产品型号+类型码+年份的最大流水号
    pattern = f"{product_model}-{type_code}-{year}-"
    last_doc = (
        db.query(Document)
        .filter(Document.doc_number.like(f"{pattern}%"))
        .order_by(Document.doc_number.desc())
        .first()
    )

    if last_doc and last_doc.doc_number:
        # 从最后一个编号中提取流水号
        parts = last_doc.doc_number.split("-")
        try:
            last_seq = int(parts[-1])
        except (ValueError, IndexError):
            last_seq = 0
        next_seq = last_seq + 1
    else:
        next_seq = 1

    seq_str = str(next_seq).zfill(rule.seq_digits)

    # 按模板生成编号
    doc_number = rule.template.format(
        product=product_model,
        code=type_code,
        year=year,
        seq=seq_str,
    )

    return JSONResponse({
        "doc_number": doc_number,
        "type_name": rule.type_name,
        "next_seq": next_seq,
    })


# ─── 快捷添加分类 API ────────────────────────────
@app.post("/api/add-category")
def api_add_category(
    request: Request,
    user: User = Depends(require_role("admin", "editor")),
    db: Session = Depends(get_db),
):
    """AJAX 快捷添加分类"""
    import json
    # 支持 JSON body
    # 此处简化处理，用 Form
    return JSONResponse({"status": "ok"})


@app.post("/api/categories/quick-add")
def api_category_quick_add(
    name: str = Form(...),
    user: User = Depends(require_role("admin", "editor")),
    db: Session = Depends(get_db),
):
    """AJAX 快捷添加分类，返回新分类 ID"""
    existing = db.query(Category).filter(Category.name == name.strip()).first()
    if existing:
        return JSONResponse({"id": existing.id, "name": existing.name, "existed": True})
    cat = Category(name=name.strip())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return JSONResponse({"id": cat.id, "name": cat.name, "existed": False})


# ─── 编号规则管理 ─────────────────────────────────
@app.get("/numbering-rules", response_class=HTMLResponse)
def numbering_rules_page(
    request: Request,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    rules = db.query(DocNumberRule).order_by(DocNumberRule.sort_order).all()
    return templates.TemplateResponse("numbering_rules.html", {
        "request": request, "user": user, "rules": rules,
    })


@app.post("/numbering-rules/add")
def numbering_rule_add(
    type_code: str = Form(...),
    type_name: str = Form(...),
    template: str = Form("{product}-{code}-{year}-{seq}"),
    seq_digits: int = Form(3),
    sort_order: int = Form(50),
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    existing = db.query(DocNumberRule).filter(DocNumberRule.type_code == type_code.upper()).first()
    if existing:
        raise HTTPException(400, f"类型码 {type_code.upper()} 已存在")
    rule = DocNumberRule(
        type_code=type_code.upper(), type_name=type_name,
        template=template, seq_digits=seq_digits, sort_order=sort_order,
    )
    db.add(rule)
    db.commit()
    return RedirectResponse("/numbering-rules", status_code=302)


@app.post("/numbering-rules/{rule_id}/delete")
def numbering_rule_delete(
    rule_id: int,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    rule = db.query(DocNumberRule).filter(DocNumberRule.id == rule_id).first()
    if rule:
        db.delete(rule)
        db.commit()
    return RedirectResponse("/numbering-rules", status_code=302)


# ─── 用户管理 ─────────────────────────────────────
@app.get("/users", response_class=HTMLResponse)
def user_list(
    request: Request,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return templates.TemplateResponse("users.html", {
        "request": request, "user": user, "users": users,
    })


@app.post("/users/add")
def user_add(
    request: Request,
    username: str = Form(...),
    display_name: str = Form(...),
    password: str = Form(...),
    role: str = Form("user"),
    department: str = Form(""),
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(400, "用户名已存在")
    new_user = User(
        username=username, display_name=display_name,
        password_hash=hash_password(password), role=role, department=department,
    )
    db.add(new_user)
    db.commit()
    return RedirectResponse("/users", status_code=302)


@app.post("/users/{user_id}/toggle")
def user_toggle(
    user_id: int,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(User.id == user_id).first()
    if target and target.username != "admin":
        target.is_active = not target.is_active
        db.commit()
    return RedirectResponse("/users", status_code=302)


# ─── 分类管理 ─────────────────────────────────────
@app.get("/categories", response_class=HTMLResponse)
def category_list(
    request: Request,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    categories = db.query(Category).order_by(Category.name).all()
    return templates.TemplateResponse("categories.html", {
        "request": request, "user": user, "categories": categories,
    })


@app.post("/categories/add")
def category_add(
    name: str = Form(...),
    description: str = Form(""),
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    cat = Category(name=name, description=description)
    db.add(cat)
    db.commit()
    return RedirectResponse("/categories", status_code=302)


@app.post("/categories/{cat_id}/delete")
def category_delete(
    cat_id: int,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    cat = db.query(Category).filter(Category.id == cat_id).first()
    if cat:
        db.delete(cat)
        db.commit()
    return RedirectResponse("/categories", status_code=302)


# ─── API 接口 ─────────────────────────────────────
@app.get("/api/documents")
def api_documents(
    q: str = "",
    product_model: str = "",
    page: int = 1,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Document)
    if q:
        query = query.filter(or_(
            Document.title.contains(q), Document.doc_number.contains(q),
        ))
    if product_model:
        query = query.filter(Document.product_model.contains(product_model))
    per_page = 20
    total = query.count()
    docs = query.offset((page-1)*per_page).limit(per_page).all()
    return {
        "total": total, "page": page,
        "items": [
            {
                "id": d.id, "title": d.title, "filename": d.filename,
                "product_model": d.product_model, "doc_number": d.doc_number,
                "doc_type_code": d.doc_type_code, "version": d.version,
                "created_at": d.created_at.isoformat(),
            }
            for d in docs
        ],
    }


# ─── 产品参数卡片 ─────────────────────────────────
@app.get("/specs", response_class=HTMLResponse)
def specs_page(
    request: Request,
    product_model: str = Query(""),
    category: str = Query(""),
    q: str = Query(""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ProductSpec)
    if product_model:
        query = query.filter(ProductSpec.product_model.contains(product_model))
    if category:
        query = query.filter(ProductSpec.spec_category == category)
    if q:
        query = query.filter(ProductSpec.spec_name.contains(q))

    total = query.count()
    specs = query.order_by(ProductSpec.product_model, ProductSpec.spec_category).limit(200).all()

    categories_list = ["电气参数", "机械参数", "环境参数", "性能参数", "安全参数", "其他"]
    return templates.TemplateResponse("specs.html", {
        "request": request, "user": user, "specs": specs, "total": total,
        "product_model": product_model, "selected_category": category, "q": q,
        "categories_list": categories_list,
    })


@app.post("/specs/add")
def spec_add(
    product_model: str = Form(...),
    product_name: str = Form(""),
    spec_category: str = Form("其他"),
    spec_name: str = Form(...),
    spec_value: str = Form(""),
    spec_unit: str = Form(""),
    standard_ref: str = Form(""),
    standard_value: str = Form(""),
    remark: str = Form(""),
    user: User = Depends(require_role("admin", "editor")),
    db: Session = Depends(get_db),
):
    spec = ProductSpec(
        product_model=product_model, product_name=product_name,
        spec_category=spec_category, spec_name=spec_name,
        spec_value=spec_value, spec_unit=spec_unit,
        standard_ref=standard_ref, standard_value=standard_value,
        remark=remark,
    )
    db.add(spec)
    db.commit()
    return RedirectResponse(f"/specs?product_model={product_model}", status_code=302)


@app.post("/specs/{spec_id}/delete")
def spec_delete(
    spec_id: int,
    user: User = Depends(require_role("admin", "editor")),
    db: Session = Depends(get_db),
):
    spec = db.query(ProductSpec).filter(ProductSpec.id == spec_id).first()
    if spec:
        db.delete(spec)
        db.commit()
    return RedirectResponse("/specs", status_code=302)


@app.post("/specs/import")
async def spec_import(
    file: UploadFile = File(...),
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    content = await file.read()
    try:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        wb.close()

        count = 0
        for row in rows[1:]:  # 跳过表头
            if not row or not row[0]:
                continue
            spec = ProductSpec(
                product_model=str(row[0] or ""),
                product_name=str(row[1] or ""),
                spec_category=str(row[2] or "其他"),
                spec_name=str(row[3] or ""),
                spec_value=str(row[4] or ""),
                spec_unit=str(row[5] or ""),
                standard_ref=str(row[6] or ""),
                standard_value=str(row[7] or ""),
                remark=str(row[8] or "") if len(row) > 8 else "",
            )
            db.add(spec)
            count += 1
        db.commit()
    except Exception as e:
        raise HTTPException(400, f"导入失败: {str(e)}")
    return RedirectResponse("/specs", status_code=302)


# ─── 知识问答 ─────────────────────────────────────
@app.get("/qa", response_class=HTMLResponse)
def qa_page(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    documents = db.query(Document).order_by(Document.updated_at.desc()).limit(100).all()
    return templates.TemplateResponse("qa.html", {
        "request": request, "user": user, "documents": documents,
    })


@app.post("/api/ask")
def api_ask(
    question: str = Form(...),
    doc_id: str = Form("all"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not is_ai_available():
        return JSONResponse({"error": "AI 未配置，请在系统管理 > AI 设置 中配置"}, status_code=400)
    try:
        context_parts = []

        # 1. 先搜索参数卡片
        specs = db.query(ProductSpec).filter(
            or_(
                ProductSpec.spec_name.contains(question),
                ProductSpec.product_model.contains(question),
                ProductSpec.remark.contains(question),
            )
        ).limit(20).all()
        if specs:
            spec_lines = ["=== 产品参数卡片 ==="]
            for s in specs:
                line = f"[{s.product_model}] {s.spec_name}: {s.spec_value} {s.spec_unit}"
                if s.standard_value:
                    line += f" (标准要求: {s.standard_value})"
                if s.standard_ref:
                    line += f" 依据: {s.standard_ref}"
                spec_lines.append(line)
            context_parts.append("\n".join(spec_lines))

        # 2. 搜索文档内容
        if doc_id and doc_id != "all":
            doc_context = search_document_context(question, int(doc_id), limit=5)
            # 搜索不到，直接取全文
            if not doc_context.strip():
                doc_context = get_all_doc_content(int(doc_id))
                if doc_context:
                    doc_context = doc_context[:8000]  # 限制长度
        else:
            doc_context = search_document_context(question, limit=5)
        if doc_context:
            context_parts.append(f"=== 文档内容 ===\n{doc_context}")

        context = "\n\n".join(context_parts)
        answer = ask_question(question, context)
        return JSONResponse({"answer": answer})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ─── 符合性检查 ───────────────────────────────────
@app.get("/compliance", response_class=HTMLResponse)
def compliance_page(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    documents = db.query(Document).order_by(Document.updated_at.desc()).limit(100).all()
    return templates.TemplateResponse("compliance.html", {
        "request": request, "user": user, "documents": documents,
    })


@app.post("/api/compliance-check")
def api_compliance_check(
    standard_doc_id: str = Form(""),
    standard_text: str = Form(""),
    bid_doc_id: str = Form(""),
    bid_text: str = Form(""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not is_ai_available():
        return JSONResponse({"error": "AI 未配置，请在系统管理 > AI 设置 中配置"}, status_code=400)
    try:
        context_parts = []

        # 1. 获取参数卡片作为参考
        all_specs = db.query(ProductSpec).order_by(ProductSpec.product_model).limit(100).all()
        if all_specs:
            spec_lines = ["=== 产品参数卡片（参考）==="]
            for s in all_specs:
                line = f"[{s.product_model}] {s.spec_category} - {s.spec_name}: {s.spec_value} {s.spec_unit}"
                if s.standard_value:
                    line += f" (标准: {s.standard_value})"
                spec_lines.append(line)
            context_parts.append("\n".join(spec_lines))

        # 2. 获取标准内容
        if standard_doc_id:
            standard_content = get_all_doc_content(int(standard_doc_id))
        else:
            standard_content = standard_text

        # 3. 获取投标内容
        if bid_doc_id:
            bid_content = get_all_doc_content(int(bid_doc_id))
        else:
            bid_content = bid_text

        if not standard_content.strip():
            return JSONResponse({"error": "技术标准/招标要求内容为空"}, status_code=400)
        if not bid_content.strip():
            return JSONResponse({"error": "投标文件内容为空"}, status_code=400)

        spec_context = "\n\n".join(context_parts)
        result = check_compliance(bid_content, standard_content + "\n\n" + spec_context)
        return JSONResponse({"result": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ─── AI 设置 ──────────────────────────────────────
@app.get("/ai-settings", response_class=HTMLResponse)
def ai_settings_page(
    request: Request,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    config = load_ai_config()
    return templates.TemplateResponse("ai_settings.html", {
        "request": request, "user": user, "config": config, "saved": False,
    })


@app.post("/ai-settings")
def ai_settings_save(
    request: Request,
    enabled: str = Form("false"),
    provider: str = Form(""),
    api_base: str = Form(""),
    api_key: str = Form(""),
    model: str = Form(""),
    max_tokens: int = Form(4096),
    temperature: float = Form(0.3),
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    config = {
        "enabled": enabled == "true",
        "provider": provider,
        "api_base": api_base.rstrip("/"),
        "api_key": api_key,
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    save_ai_config(config)
    return templates.TemplateResponse("ai_settings.html", {
        "request": request, "user": user, "config": config, "saved": True,
    })


@app.post("/api/test-ai")
def api_test_ai(
    user: User = Depends(require_role("admin")),
):
    config = load_ai_config()
    if not config.get("api_key"):
        return JSONResponse({"success": False, "error": "未配置 API 密钥"})
    try:
        answer = ask_question("请用一句话回复：你好，你是谁？")
        if answer.startswith("["):
            return JSONResponse({"success": False, "error": answer})
        return JSONResponse({"success": True, "response": answer[:200]})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})


# ─── 启动 ─────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print(f"启动服务: http://{HOST}:{PORT}")
    print(f"局域网访问: http://<你的IP>:{PORT}")
    uvicorn.run(app, host=HOST, port=PORT)
