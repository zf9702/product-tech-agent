# 产品技术资料管理系统 - 项目交接文档
# Product Technical Document Management System - Handoff Guide
# 生成时间: 2026-04-25

## 项目概述

为航空设备测试团队构建的 Web 文档管理系统，支持文档管理、AI 知识问答、
投标文件符合性检查。直接运行在 Windows 上，无需 Docker。

## 技术栈

- FastAPI + Uvicorn (Web 框架)
- SQLite + SQLAlchemy (数据库)
- Fernet 对称加密 (文档加密存储)
- JWT 认证 (用户登录)
- Pywin32 COM (WPS/Word 文档预览)
- MiMo-v2.5 API (AI 问答)

## 目录结构

```
D:\工作文件\产品技术资料Agent\tech-doc-agent\
├── app.py              主程序 (路由 + 启动)
├── config.py           配置 (路径、密钥、端口)
├── database.py         数据库模型 (User/Document/Category/DocNumberRule/ProductSpec/AccessLog)
├── auth.py             JWT 认证 + 密码哈希
├── encryption.py       Fernet 文件加密/解密
├── doc_parser.py       文档内容提取 + FTS5/LIKE 全文检索
├── ai_engine.py        AI 模型接口 (可配置后端)
├── office_convert.py   WPS/Word COM 自动化 (docx→PDF)
├── requirements.txt    Python 依赖
├── 启动服务.bat         Windows 启动脚本
├── .gitignore          Git 忽略规则
├── ai_config.json      AI 配置 (不入 Git)
├── templates/          Jinja2 HTML 模板 (10个)
│   ├── base.html       基础布局 + 侧边栏
│   ├── login.html      登录页
│   ├── dashboard.html  仪表盘
│   ├── documents.html  文档列表 (含批量删除)
│   ├── upload.html     单个上传 (自动编号 + 快捷分类)
│   ├── batch_upload.html 批量上传
│   ├── preview.html    在线预览 (PDF/图片/Word)
│   ├── document_detail.html 文档详情
│   ├── users.html      用户管理
│   ├── categories.html 分类管理
│   ├── numbering_rules.html 编号规则管理
│   ├── specs.html      产品参数卡片
│   ├── qa.html         知识问答 (聊天式)
│   ├── compliance.html 符合性检查
│   └── ai_settings.html AI 设置
├── data/               加密文件存储 (不入 Git)
│   └── pdf_cache/      Word→PDF 转换缓存
└── database/           SQLite 数据库 (不入 Git)
    └── app.db
```

## 已完成功能

1. 用户认证 - JWT + bcrypt, 三级权限 (admin/editor/user)
2. 文档管理 - 上传/下载/删除/详情, Fernet 加密存储
3. 批量上传 - 多文件拖拽, 自动编号, 进度显示
4. 自动编号 - 按国标规范 (产品型号-类型码-年份-流水号)
5. 在线预览 - PDF(浏览器), 图片(直接显示), Word(WPS COM→PDF)
6. 批量删除 - 勾选+确认+逐个删除
7. 全文检索 - FTS5 + LIKE 中文回退, 标题+内容搜索
8. 分类管理 - 自定义添加, 上传页快捷添加
9. 编号规则 - 10个预置规则, 管理员可增删
10. 产品参数卡片 - 手动录入 + Excel批量导入
11. 知识问答 - 聊天式, 同时搜索参数卡片+文档内容
12. 符合性检查 - 标准 vs 投标文件, AI 逐条比对
13. AI 设置 - 支持 DeepSeek/OpenAI/通义千问/MiMo
14. 操作日志 - 记录上传/下载/查看操作
15. 局域网部署 - 防火墙端口 8080 已开放

## 未完成 / 待办

1. GitHub 推送 - 仓库已建 https://github.com/zf9702/product-tech-agent
   需要用户提供 Personal Access Token 才能推送
2. 修改密码功能 - admin 用户还没有改密码入口
3. 数据备份工具 - 一键备份数据库和文件
4. MS 系统集成 - 第二阶段规划

## 关键 Bug 修复记录

| 问题 | 原因 | 修复 |
|------|------|------|
| 上传 500 错误 | AccessLog 引用 doc.id 但 doc 未 flush | db.flush() before creating log |
| 下载中文文件名崩溃 | HTTP header Latin-1 编码 | RFC 5987: filename*=UTF-8''quote() |
| AI 问答超时 | GBK 编码读不了 emoji | raw=resp.read() then decode UTF-8 |
| FTS5 中文搜索无结果 | unicode61 不支持中文分词 | LIKE fallback on content+title |
| 批量上传全部失败 | fetch redirect:'manual' 返回 status 0 | 改用 redirect:'follow' |
| AI 设置保存 500 | request 变量未定义 | 加 request: Request 参数 |
| bcrypt 崩溃 | passlib 与 bcrypt>=4.1 不兼容 | pin bcrypt==4.0.1 |
| 数据库缺列 | ALTER TABLE 不自动执行 | 手动 PRAGMA + ALTER |

## 登录信息

- 地址: http://localhost:8080 (本机) 或 http://10.14.241.37:8080 (局域网)
- 默认管理员: admin / admin123
- AI 模型: MiMo-v2.5 (配置在 ai_config.json)

## 启动方式

双击 "启动服务.bat" 或命令行: python app.py

## GitHub 推送步骤

```bash
git init
git add .
git commit -m "产品技术资料管理系统 v1.0"
git remote add origin https://github.com/zf9702/product-tech-agent.git
git push -u origin master
```

需要配置 GitHub Token:
```bash
git config --global credential.helper store
git config --global user.name "zf9702"
git config --global user.email "your-email@example.com"
```
