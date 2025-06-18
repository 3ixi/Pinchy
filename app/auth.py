"""
认证相关功能
"""
import os
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends, Cookie
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from app.database import get_db
from app.models import User

# 加载 .env 文件中的环境变量
load_dotenv()

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT配置（请务必修改SECRET_KEY第二个引号内内容）
SECRET_KEY = os.getenv("SECRET_KEY", "Pinchy-Secret-Key-gUvFfAvIiOlNoY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080

security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None, system_uuid: Optional[str] = None):
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})

    # 增强安全性：添加系统UUID到payload
    if system_uuid:
        to_encode.update({"system_uuid": system_uuid})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str, system_uuid: Optional[str] = None) -> Optional[str]:
    """验证令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            return None

        # 增强安全性：验证系统UUID（如果提供）
        if system_uuid:
            token_system_uuid = payload.get("system_uuid")
            if token_system_uuid and token_system_uuid != system_uuid:
                return None

        return username
    except JWTError:
        return None

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """验证用户"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user

def get_current_user(token: Optional[str] = Cookie(None, alias="access_token"), db: Session = Depends(get_db)):
    """获取当前用户"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未找到访问令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 获取系统UUID用于验证
    from app.routers.settings import get_or_create_system_uuid
    try:
        system_uuid = get_or_create_system_uuid(db)
    except Exception:
        system_uuid = None

    username = verify_token(token, system_uuid)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的访问令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def init_admin_user(db: Session):
    """初始化管理员用户"""
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        # 默认密码为 admin，建议首次登录后修改
        hashed_password = get_password_hash("admin")
        admin_user = User(username="admin", password_hash=hashed_password)
        db.add(admin_user)
        db.commit()
        print("已创建默认管理员用户: admin/admin")
