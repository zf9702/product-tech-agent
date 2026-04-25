"""
Office 文档转 PDF 工具
优先使用 WPS，其次 MS Word，都不可用则回退到 mammoth.js
"""
import os
import subprocess
import tempfile
import time
from pathlib import Path
from config import DATA_DIR

# 缓存目录
PDF_CACHE_DIR = DATA_DIR / "pdf_cache"
PDF_CACHE_DIR.mkdir(exist_ok=True)


def _find_wps():
    """查找 WPS 安装路径"""
    common_paths = [
        r"C:\Users\{}\AppData\Local\Kingsoft\WPS Office\12.1.0.19309\office6\wps.exe".format(os.environ.get("USERNAME", "")),
        r"C:\Program Files\Kingsoft\WPS Office\12.1.0.19309\office6\wps.exe",
        r"C:\Program Files (x86)\Kingsoft\WPS Office\12.1.0.19309\office6\wps.exe",
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p
    # 通用查找
    local_app = os.environ.get("LOCALAPPDATA", "")
    if local_app:
        wps_root = Path(local_app) / "Kingsoft" / "WPS Office"
        if wps_root.exists():
            for d in sorted(wps_root.iterdir(), reverse=True):
                exe = d / "office6" / "wps.exe"
                if exe.exists():
                    return str(exe)
    return None


def _find_word():
    """查找 MS Word 安装路径"""
    common_paths = [
        r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
        r"C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE",
        r"C:\Program Files\Microsoft Office\Office16\WINWORD.EXE",
        r"C:\Program Files (x86)\Microsoft Office\Office16\WINWORD.EXE",
        r"C:\Program Files\Microsoft Office\Office15\WINWORD.EXE",
        r"C:\Program Files (x86)\Microsoft Office\Office15\WINWORD.EXE",
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p
    return None


def _find_libreoffice():
    """查找 LibreOffice"""
    common_paths = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p
    return None


def _convert_with_wps(docx_path: str, pdf_path: str) -> bool:
    """用 WPS 转换 docx -> pdf"""
    wps_exe = _find_wps()
    if not wps_exe:
        return False
    try:
        import win32com.client
        import pythoncom
        pythoncom.CoInitialize()
        try:
            wps = win32com.client.Dispatch("KWPS.Application")
            wps.Visible = False
            doc = wps.Documents.Open(docx_path)
            doc.SaveAs(pdf_path, FileFormat=17)  # 17 = wdFormatPDF
            doc.Close()
            wps.Quit()
            return True
        except Exception:
            try:
                wps.Quit()
            except:
                pass
            return False
        finally:
            pythoncom.CoUninitialize()
    except ImportError:
        # 没有 pywin32，尝试命令行方式
        return False


def _convert_with_word(docx_path: str, pdf_path: str) -> bool:
    """用 MS Word 转换 docx -> pdf"""
    word_exe = _find_word()
    if not word_exe:
        return False
    try:
        import win32com.client
        import pythoncom
        pythoncom.CoInitialize()
        try:
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            doc = word.Documents.Open(docx_path)
            doc.SaveAs(pdf_path, FileFormat=17)  # 17 = wdFormatPDF
            doc.Close()
            word.Quit()
            return True
        except Exception:
            try:
                word.Quit()
            except:
                pass
            return False
        finally:
            pythoncom.CoUninitialize()
    except ImportError:
        return False


def _convert_with_libreoffice(docx_path: str, pdf_path: str) -> bool:
    """用 LibreOffice 转换 docx -> pdf"""
    lo_exe = _find_libreoffice()
    if not lo_exe:
        return False
    try:
        out_dir = os.path.dirname(pdf_path)
        result = subprocess.run(
            [lo_exe, "--headless", "--convert-to", "pdf", "--outdir", out_dir, docx_path],
            capture_output=True, timeout=30,
        )
        # LibreOffice 输出文件名基于输入文件名
        expected_pdf = os.path.join(out_dir, Path(docx_path).stem + ".pdf")
        if os.path.exists(expected_pdf):
            if expected_pdf != pdf_path:
                os.rename(expected_pdf, pdf_path)
            return True
        return False
    except Exception:
        return False


def docx_to_pdf(docx_path: str, doc_id: int) -> str:
    """
    将 docx 转为 pdf，返回 pdf 路径
    使用缓存避免重复转换
    """
    cache_path = str(PDF_CACHE_DIR / f"{doc_id}.pdf")

    # 如果缓存存在且比源文件新，直接返回
    if os.path.exists(cache_path):
        if os.path.getmtime(cache_path) >= os.path.getmtime(docx_path):
            return cache_path

    # 依次尝试三种方式
    if _convert_with_word(docx_path, cache_path):
        return cache_path
    if _convert_with_wps(docx_path, cache_path):
        return cache_path
    if _convert_with_libreoffice(docx_path, cache_path):
        return cache_path

    return None  # 转换失败


def get_office_type():
    """检测可用的 Office 类型"""
    if _find_word():
        return "MS Word"
    if _find_wps():
        return "WPS"
    if _find_libreoffice():
        return "LibreOffice"
    return None
