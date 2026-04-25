"""
产品技术资料管理系统 - 配置文件
"""
import os
from pathlib import Path

# 基础路径
BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"
DB_DIR = BASE_DIR / "database"

# 确保目录存在
DATA_DIR.mkdir(exist_ok=True)
DB_DIR.mkdir(exist_ok=True)

# 数据库
DATABASE_URL = f"sqlite:///{DB_DIR / 'app.db'}"

# 加密密钥（首次运行自动生成，请妥善保管）
SECRET_KEY_FILE = BASE_DIR / ".secret_key"
if SECRET_KEY_FILE.exists():
    SECRET_KEY = SECRET_KEY_FILE.read_text().strip()
else:
    import secrets
    SECRET_KEY = secrets.token_hex(32)
    SECRET_KEY_FILE.write_text(SECRET_KEY)

# 文档加密密钥
DOC_KEY_FILE = BASE_DIR / ".doc_key"
if DOC_KEY_FILE.exists():
    DOC_ENCRYPT_KEY = DOC_KEY_FILE.read_bytes()
else:
    from cryptography.fernet import Fernet
    DOC_ENCRYPT_KEY = Fernet.generate_key()
    DOC_KEY_FILE.write_bytes(DOC_ENCRYPT_KEY)

# JWT 配置
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 480  # 8小时

# 服务配置
HOST = "0.0.0.0"  # 局域网可访问
PORT = 8080

# 文件上传限制 (MB)
MAX_UPLOAD_SIZE_MB = 100

# 允许的文件类型
ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".ppt", ".pptx", ".txt", ".md", ".dwg", ".dxf",
    ".png", ".jpg", ".jpeg", ".zip", ".rar", ".7z",
    ".xml", ".json", ".csv",
}
