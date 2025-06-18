"""
环境变量管理相关路由
"""
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.auth import get_current_user
from app.models import User, EnvironmentVariable

router = APIRouter(prefix="/api/env", tags=["环境变量管理"])

def to_local_time(dt):
    """将UTC时间转换为本地时间"""
    if dt is None:
        return None

    # 如果datetime对象没有时区信息，假设它是UTC时间
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # 转换为本地时间
    local_dt = dt.astimezone()
    return local_dt.isoformat()

class EnvVarCreate(BaseModel):
    key: str
    value: str
    description: Optional[str] = None

class EnvVarUpdate(BaseModel):
    value: Optional[str] = None
    description: Optional[str] = None

class EnvVarResponse(BaseModel):
    id: int
    key: str
    value: str
    description: Optional[str]
    created_at: str
    updated_at: Optional[str]

    class Config:
        from_attributes = True

@router.post("/", response_model=EnvVarResponse)
async def create_env_var(
    env_data: EnvVarCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建环境变量"""
    # 检查环境变量名是否已存在
    existing_var = db.query(EnvironmentVariable).filter(EnvironmentVariable.key == env_data.key).first()
    if existing_var:
        raise HTTPException(status_code=400, detail="环境变量名已存在")
    
    # 创建环境变量
    env_var = EnvironmentVariable(
        key=env_data.key,
        value=env_data.value,
        description=env_data.description
    )
    
    db.add(env_var)
    db.commit()
    db.refresh(env_var)
    
    return EnvVarResponse(
        id=env_var.id,
        key=env_var.key,
        value=env_var.value,
        description=env_var.description,
        created_at=to_local_time(env_var.created_at),
        updated_at=to_local_time(env_var.updated_at)
    )

@router.get("/", response_model=List[EnvVarResponse])
async def get_env_vars(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取所有环境变量（仅用户创建的）"""
    # 只返回非系统级的环境变量
    env_vars = db.query(EnvironmentVariable).filter(EnvironmentVariable.is_system == False).all()
    return [
        EnvVarResponse(
            id=var.id,
            key=var.key,
            value=var.value,
            description=var.description,
            created_at=to_local_time(var.created_at),
            updated_at=to_local_time(var.updated_at)
        )
        for var in env_vars
    ]

@router.get("/{var_id}", response_model=EnvVarResponse)
async def get_env_var(
    var_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取单个环境变量"""
    env_var = db.query(EnvironmentVariable).filter(EnvironmentVariable.id == var_id).first()
    if not env_var:
        raise HTTPException(status_code=404, detail="环境变量不存在")
    
    return EnvVarResponse(
        id=env_var.id,
        key=env_var.key,
        value=env_var.value,
        description=env_var.description,
        created_at=to_local_time(env_var.created_at),
        updated_at=to_local_time(env_var.updated_at)
    )

@router.put("/{var_id}", response_model=EnvVarResponse)
async def update_env_var(
    var_id: int,
    env_data: EnvVarUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新环境变量"""
    env_var = db.query(EnvironmentVariable).filter(EnvironmentVariable.id == var_id).first()
    if not env_var:
        raise HTTPException(status_code=404, detail="环境变量不存在")
    
    # 更新字段
    update_data = env_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(env_var, field, value)
    
    db.commit()
    db.refresh(env_var)
    
    return EnvVarResponse(
        id=env_var.id,
        key=env_var.key,
        value=env_var.value,
        description=env_var.description,
        created_at=to_local_time(env_var.created_at),
        updated_at=to_local_time(env_var.updated_at)
    )

@router.delete("/{var_id}")
async def delete_env_var(
    var_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除环境变量"""
    env_var = db.query(EnvironmentVariable).filter(EnvironmentVariable.id == var_id).first()
    if not env_var:
        raise HTTPException(status_code=404, detail="环境变量不存在")
    
    db.delete(env_var)
    db.commit()
    
    return {"message": f"环境变量 {env_var.key} 已删除"}
