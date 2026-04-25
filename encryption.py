"""
文档加密/解密工具
使用 Fernet 对称加密（AES-128-CBC）
"""
import os
import shutil
from pathlib import Path
from cryptography.fernet import Fernet
from config import DATA_DIR, DOC_ENCRYPT_KEY

fernet = Fernet(DOC_ENCRYPT_KEY)


def encrypt_file(source_path: str, stored_name: str) -> Path:
    """
    加密文件并存储到 data/ 目录
    返回存储路径
    """
    dest = DATA_DIR / stored_name
    with open(source_path, "rb") as f:
        plaintext = f.read()
    ciphertext = fernet.encrypt(plaintext)
    with open(dest, "wb") as f:
        f.write(ciphertext)
    return dest


def decrypt_file(stored_name: str) -> bytes:
    """
    解密文件，返回明文字节
    """
    source = DATA_DIR / stored_name
    with open(source, "rb") as f:
        ciphertext = f.read()
    return fernet.decrypt(ciphertext)


def delete_file(stored_name: str) -> bool:
    """
    删除加密存储的文件
    """
    target = DATA_DIR / stored_name
    if target.exists():
        target.unlink()
        return True
    return False
