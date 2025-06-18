"""
数据库配置和连接管理
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# 数据库文件路径
DATABASE_URL = "sqlite:///./pinchy.db"
ASYNC_DATABASE_URL = "sqlite+aiosqlite:///./pinchy.db"

# 创建同步数据库引擎
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# 创建异步数据库引擎
async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

# 创建基础模型类
Base = declarative_base()

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db():
    """获取异步数据库会话"""
    async with AsyncSessionLocal() as session:
        yield session

def create_tables():
    """创建所有数据表"""
    Base.metadata.create_all(bind=engine)

def ensure_directories():
    """确保必要的目录存在"""
    directories = ["scripts", "logs"]
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
