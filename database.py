"""
数据库模型定义
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean,
    ForeignKey, create_engine, event
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from config import DATABASE_URL

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    password_hash = Column(String(128), nullable=False)
    role = Column(String(20), default="user")  # admin / editor / viewer
    department = Column(String(100), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    documents = relationship("Document", back_populates="uploader")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, default="")
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

    children = relationship("Category", backref="parent", remote_side=[id])
    documents = relationship("Document", back_populates="category")


class DocNumberRule(Base):
    """
    文件编号规则 - 按国标规范
    编号格式: {产品型号}-{文件类型码}-{年份}-{流水号}
    例如: BY-6B-TD-2026-001
    """
    __tablename__ = "doc_number_rules"

    id = Column(Integer, primary_key=True)
    type_code = Column(String(20), unique=True, nullable=False)   # TD, DW, JS, JY...
    type_name = Column(String(100), nullable=False)               # 技术条件, 图纸...
    template = Column(String(200), default="{product}-{code}-{year}-{seq}")
    seq_digits = Column(Integer, default=3)  # 流水号位数
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, default="")
    filename = Column(String(300), nullable=False)
    stored_name = Column(String(300), nullable=False)
    file_size = Column(Integer, default=0)
    file_type = Column(String(20), default="")
    product_model = Column(String(100), default="", index=True)
    doc_number = Column(String(100), default="", index=True)
    doc_type_code = Column(String(20), default="", index=True)
    version = Column(String(50), default="1.0")
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    access_level = Column(String(20), default="public")
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    uploader = relationship("User", back_populates="documents")
    category = relationship("Category", back_populates="documents")
    logs = relationship("AccessLog", back_populates="document")


class ProductSpec(Base):
    """
    产品技术参数卡片
    结构化存储产品关键技术指标，用于精准问答和符合性检查
    """
    __tablename__ = "product_specs"

    id = Column(Integer, primary_key=True)
    # 产品信息
    product_model = Column(String(100), nullable=False, index=True)  # 产品型号
    product_name = Column(String(200), default="")                   # 产品名称
    # 参数信息
    spec_category = Column(String(100), default="", index=True)  # 参数类别（电气/机械/环境/性能）
    spec_name = Column(String(200), nullable=False)              # 参数名称
    spec_value = Column(String(500), default="")                 # 参数值
    spec_unit = Column(String(50), default="")                   # 单位
    # 标准要求
    standard_ref = Column(String(200), default="")   # 依据标准（如 GJB-xxx）
    standard_value = Column(String(500), default="") # 标准要求值
    # 备注
    remark = Column(Text, default="")
    # 来源
    source_doc_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AccessLog(Base):
    __tablename__ = "access_logs"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(20), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(50), default="")

    document = relationship("Document", back_populates="logs")
    user = relationship("User")


# 数据库引擎与会话
engine = create_engine(DATABASE_URL, echo=False)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
