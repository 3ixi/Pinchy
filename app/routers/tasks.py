"""
任务管理相关路由
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
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
    group_name: Optional[str] = "默认"

class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    script_path: Optional[str] = None
    script_type: Optional[str] = None
    cron_expression: Optional[str] = None
    environment_vars: Optional[dict] = None
    group_name: Optional[str] = None
    is_active: Optional[bool] = None

class TaskResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    script_path: str
    script_type: str
    cron_expression: str
    environment_vars: dict
    group_name: str
    is_active: bool
    created_at: str
    updated_at: Optional[str]

    class Config:
        from_attributes = True

class PaginatedTasksResponse(BaseModel):
    tasks: List[TaskResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class TaskGroupsResponse(BaseModel):
    groups: List[str]

class TaskStatsResponse(BaseModel):
    total_tasks: int
    active_tasks: int

class GroupRenameRequest(BaseModel):
    old_name: str
    new_name: str

class GroupDeleteRequest(BaseModel):
    group_name: str

class GroupCreateRequest(BaseModel):
    group_name: str

def validate_cron_expression(cron_expr: str) -> bool:
    """验证cron表达式格式，支持5字段和6字段（包含秒）格式"""
    parts = cron_expr.split()

    # 支持5字段（传统格式）和6字段（包含秒）格式
    if len(parts) not in [5, 6]:
        return False

    # 验证每个部分的基本格式
    for part in parts:
        if not (part == '*' or part.isdigit() or '/' in part or '-' in part or ',' in part):
            return False

    # 如果是6字段格式，验证秒字段（第一个字段）的范围
    if len(parts) == 6:
        seconds_part = parts[0]
        if seconds_part != '*' and not _validate_cron_field_range(seconds_part, 0, 59):
            return False

    return True

def _validate_cron_field_range(field: str, min_val: int, max_val: int) -> bool:
    """验证cron字段的数值范围"""
    try:
        # 处理简单数字
        if field.isdigit():
            val = int(field)
            return min_val <= val <= max_val

        # 处理逗号分隔的多个值
        if ',' in field:
            for part in field.split(','):
                if not _validate_cron_field_range(part.strip(), min_val, max_val):
                    return False
            return True

        # 处理范围表达式 (如 0-30)
        if '-' in field and '/' not in field:
            start, end = field.split('-', 1)
            if start.isdigit() and end.isdigit():
                start_val, end_val = int(start), int(end)
                return min_val <= start_val <= end_val <= max_val

        # 处理步长表达式 (如 */5 或 0-30/5)
        if '/' in field:
            base, step = field.split('/', 1)
            if not step.isdigit():
                return False

            step_val = int(step)
            if step_val <= 0 or step_val > max_val:
                return False

            if base == '*':
                return True
            elif base.isdigit():
                val = int(base)
                return min_val <= val <= max_val
            elif '-' in base:
                start, end = base.split('-', 1)
                if start.isdigit() and end.isdigit():
                    start_val, end_val = int(start), int(end)
                    return min_val <= start_val <= end_val <= max_val

        return True
    except (ValueError, IndexError):
        return False

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
        group_name=task_data.group_name or "默认",
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
        group_name=task.group_name,
        is_active=task.is_active,
        created_at=format_datetime(task.created_at, db),
        updated_at=format_datetime(task.updated_at, db) if task.updated_at else None
    )

@router.get("/", response_model=PaginatedTasksResponse)
async def get_tasks(
    group_name: Optional[str] = Query(None, description="任务分组名称"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(30, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取任务列表（支持分组和分页）"""
    # 构建查询
    query = db.query(Task)

    # 过滤掉占位任务（以__GROUP_PLACEHOLDER_开头的任务）
    query = query.filter(~Task.name.like('__GROUP_PLACEHOLDER_%'))

    # 按分组过滤
    if group_name:
        query = query.filter(Task.group_name == group_name)

    # 获取总数
    total = query.count()

    # 分页
    offset = (page - 1) * page_size
    tasks = query.offset(offset).limit(page_size).all()

    # 计算总页数
    total_pages = (total + page_size - 1) // page_size

    return PaginatedTasksResponse(
        tasks=[
            TaskResponse(
                id=task.id,
                name=task.name,
                description=task.description,
                script_path=task.script_path,
                script_type=task.script_type,
                cron_expression=task.cron_expression,
                environment_vars=task.environment_vars,
                group_name=task.group_name,
                is_active=task.is_active,
                created_at=format_datetime(task.created_at, db),
                updated_at=format_datetime(task.updated_at, db) if task.updated_at else None
            )
            for task in tasks
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@router.get("/groups", response_model=TaskGroupsResponse)
async def get_task_groups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取所有任务分组"""
    groups = db.query(Task.group_name).distinct().all()
    group_names = [group[0] for group in groups]

    # 确保"默认"分组总是存在
    if "默认" not in group_names:
        group_names.insert(0, "默认")

    return TaskGroupsResponse(groups=group_names)

@router.post("/groups/create")
async def create_task_group(
    create_data: GroupCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建新的任务分组"""
    group_name = create_data.group_name.strip()

    # 验证输入
    if not group_name:
        raise HTTPException(status_code=400, detail="分组名称不能为空")

    # 检查分组名称是否已存在
    existing_group = db.query(Task).filter(Task.group_name == group_name).first()
    if existing_group:
        raise HTTPException(status_code=400, detail="分组名称已存在")

    # 由于分组是通过任务来管理的，我们需要创建一个占位任务
    # 这个任务不会被执行，只是为了在数据库中建立分组
    placeholder_task = Task(
        name=f"__GROUP_PLACEHOLDER_{group_name}",
        description=f"分组 '{group_name}' 的占位任务，请勿删除",
        script_path="# 这是一个占位脚本，用于维护分组结构",
        script_type="python",
        cron_expression="0 0 1 1 *",  # 每年1月1日执行（实际不会执行因为is_active=False）
        group_name=group_name,
        is_active=False  # 确保不会被执行
    )

    db.add(placeholder_task)
    db.commit()

    return {"message": f"分组 '{group_name}' 创建成功"}

@router.get("/stats", response_model=TaskStatsResponse)
async def get_task_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取任务统计信息"""
    # 过滤掉占位任务（以__GROUP_PLACEHOLDER_开头的任务）
    total_tasks = db.query(Task).filter(~Task.name.like('__GROUP_PLACEHOLDER_%')).count()
    active_tasks = db.query(Task).filter(
        Task.is_active == True,
        ~Task.name.like('__GROUP_PLACEHOLDER_%')
    ).count()

    return TaskStatsResponse(
        total_tasks=total_tasks,
        active_tasks=active_tasks
    )

@router.put("/groups/rename")
async def rename_task_group(
    rename_data: GroupRenameRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """重命名任务分组"""
    old_name = rename_data.old_name
    new_name = rename_data.new_name

    # 验证输入
    if not old_name or not new_name:
        raise HTTPException(status_code=400, detail="分组名称不能为空")

    if old_name == new_name:
        raise HTTPException(status_code=400, detail="新分组名称与原名称相同")

    # 检查原分组是否存在
    existing_tasks = db.query(Task).filter(Task.group_name == old_name).first()
    if not existing_tasks:
        raise HTTPException(status_code=404, detail="原分组不存在")

    # 检查新分组名称是否已存在
    existing_new_group = db.query(Task).filter(Task.group_name == new_name).first()
    if existing_new_group:
        raise HTTPException(status_code=400, detail="新分组名称已存在")

    # 更新所有该分组下的任务
    updated_count = db.query(Task).filter(Task.group_name == old_name).update(
        {Task.group_name: new_name}
    )
    db.commit()

    return {"message": f"分组 '{old_name}' 已重命名为 '{new_name}'，共更新 {updated_count} 个任务"}

@router.delete("/groups/delete")
async def delete_task_group(
    delete_data: GroupDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除任务分组及其下所有任务"""
    group_name = delete_data.group_name

    # 验证输入
    if not group_name:
        raise HTTPException(status_code=400, detail="分组名称不能为空")

    # 不允许删除"默认"分组
    if group_name == "默认":
        raise HTTPException(status_code=400, detail="不能删除默认分组")

    # 检查分组是否存在
    tasks_in_group = db.query(Task).filter(Task.group_name == group_name).all()
    if not tasks_in_group:
        raise HTTPException(status_code=404, detail="分组不存在")

    # 从调度器中移除所有任务
    for task in tasks_in_group:
        task_scheduler.remove_task(task.id)

    # 删除所有该分组下的任务
    deleted_count = db.query(Task).filter(Task.group_name == group_name).delete()
    db.commit()

    return {"message": f"分组 '{group_name}' 及其下 {deleted_count} 个任务已删除"}

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
        group_name=task.group_name,
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
        group_name=task.group_name,
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
