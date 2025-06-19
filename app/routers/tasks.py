"""
任务管理相关路由
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.auth import get_current_user
from app.models import User, Task
from app.scheduler import task_scheduler
from app.timezone_utils import format_datetime

router = APIRouter(prefix="/api/tasks", tags=["任务管理"])

class TaskCreate(BaseModel):
    name: str
    description: Optional[str] = None
    script_path: str
    script_type: str  # python 或 nodejs
    cron_expression: str
    environment_vars: Optional[dict] = {}

class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    script_path: Optional[str] = None
    script_type: Optional[str] = None
    cron_expression: Optional[str] = None
    environment_vars: Optional[dict] = None
    is_active: Optional[bool] = None

class TaskResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    script_path: str
    script_type: str
    cron_expression: str
    environment_vars: dict
    is_active: bool
    created_at: str
    updated_at: Optional[str]

    class Config:
        from_attributes = True

def validate_cron_expression(cron_expr: str) -> bool:
    """验证cron表达式格式"""
    parts = cron_expr.split()
    if len(parts) != 5:
        return False
    
    # 简单验证每个部分
    for part in parts:
        if not (part == '*' or part.isdigit() or '/' in part or '-' in part or ',' in part):
            return False
    
    return True

@router.post("/", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建新任务"""
    # 验证脚本类型
    if task_data.script_type not in ["python", "nodejs"]:
        raise HTTPException(status_code=400, detail="脚本类型必须是 python 或 nodejs")
    
    # 验证cron表达式
    if not validate_cron_expression(task_data.cron_expression):
        raise HTTPException(status_code=400, detail="无效的cron表达式格式")
    
    # 检查任务名称是否重复
    existing_task = db.query(Task).filter(Task.name == task_data.name).first()
    if existing_task:
        raise HTTPException(status_code=400, detail="任务名称已存在")
    
    # 创建任务
    task = Task(
        name=task_data.name,
        description=task_data.description,
        script_path=task_data.script_path,
        script_type=task_data.script_type,
        cron_expression=task_data.cron_expression,
        environment_vars=task_data.environment_vars or {},
        is_active=True
    )
    
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # 添加到调度器
    task_scheduler.add_task(task)
    
    return TaskResponse(
        id=task.id,
        name=task.name,
        description=task.description,
        script_path=task.script_path,
        script_type=task.script_type,
        cron_expression=task.cron_expression,
        environment_vars=task.environment_vars,
        is_active=task.is_active,
        created_at=format_datetime(task.created_at, db),
        updated_at=format_datetime(task.updated_at, db) if task.updated_at else None
    )

@router.get("/", response_model=List[TaskResponse])
async def get_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取所有任务"""
    tasks = db.query(Task).all()
    return [
        TaskResponse(
            id=task.id,
            name=task.name,
            description=task.description,
            script_path=task.script_path,
            script_type=task.script_type,
            cron_expression=task.cron_expression,
            environment_vars=task.environment_vars,
            is_active=task.is_active,
            created_at=format_datetime(task.created_at, db),
            updated_at=format_datetime(task.updated_at, db) if task.updated_at else None
        )
        for task in tasks
    ]

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取单个任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return TaskResponse(
        id=task.id,
        name=task.name,
        description=task.description,
        script_path=task.script_path,
        script_type=task.script_type,
        cron_expression=task.cron_expression,
        environment_vars=task.environment_vars,
        is_active=task.is_active,
        created_at=format_datetime(task.created_at, db),
        updated_at=format_datetime(task.updated_at, db) if task.updated_at else None
    )

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 验证脚本类型
    if task_data.script_type and task_data.script_type not in ["python", "nodejs"]:
        raise HTTPException(status_code=400, detail="脚本类型必须是 python 或 nodejs")
    
    # 验证cron表达式
    if task_data.cron_expression and not validate_cron_expression(task_data.cron_expression):
        raise HTTPException(status_code=400, detail="无效的cron表达式格式")
    
    # 检查任务名称是否重复
    if task_data.name and task_data.name != task.name:
        existing_task = db.query(Task).filter(Task.name == task_data.name).first()
        if existing_task:
            raise HTTPException(status_code=400, detail="任务名称已存在")
    
    # 更新任务字段
    update_data = task_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    
    db.commit()
    db.refresh(task)
    
    # 更新调度器中的任务
    task_scheduler.remove_task(task.id)
    if task.is_active:
        task_scheduler.add_task(task)
    
    return TaskResponse(
        id=task.id,
        name=task.name,
        description=task.description,
        script_path=task.script_path,
        script_type=task.script_type,
        cron_expression=task.cron_expression,
        environment_vars=task.environment_vars,
        is_active=task.is_active,
        created_at=format_datetime(task.created_at, db),
        updated_at=format_datetime(task.updated_at, db) if task.updated_at else None
    )

@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 从调度器中移除任务
    task_scheduler.remove_task(task.id)
    
    # 删除任务
    db.delete(task)
    db.commit()
    
    return {"message": f"任务 {task.name} 已删除"}

@router.post("/{task_id}/toggle")
async def toggle_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """启用/禁用任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 切换任务状态
    task.is_active = not task.is_active
    db.commit()
    
    # 更新调度器
    if task.is_active:
        task_scheduler.add_task(task)
    else:
        task_scheduler.remove_task(task.id)
    
    status = "启用" if task.is_active else "禁用"
    return {"message": f"任务 {task.name} 已{status}"}


@router.post("/{task_id}/run")
async def run_task_immediately(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """立即运行任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    try:
        # 立即执行任务
        task_scheduler.run_task_immediately(task_id)
        return {"message": f"任务 {task.name} 已提交执行"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"执行任务失败: {str(e)}")

@router.post("/{task_id}/stop")
async def stop_task(
    task_id: int,
    force: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """停止正在运行的任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 检查任务是否正在运行
    if task_id not in task_scheduler.running_tasks:
        raise HTTPException(status_code=400, detail="任务未在运行中")

    try:
        # 停止任务
        success = await task_scheduler.stop_task(task_id, force=force)

        if success:
            return {"message": f"任务 {task.name} 已{'强制' if force else ''}停止"}
        else:
            raise HTTPException(status_code=500, detail="停止任务失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止任务失败: {str(e)}")

@router.get("/running/status")
async def get_running_tasks_status(
    current_user: User = Depends(get_current_user)
):
    """获取所有正在运行的任务状态"""
    return {
        "running_tasks": list(task_scheduler.running_tasks.keys())
    }
