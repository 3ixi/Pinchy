"""
日志管理相关路由
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel, field_validator
import asyncio
from datetime import datetime
from app.database import get_db
from app.auth import get_current_user
from app.models import User, TaskLog
from app.websocket_manager import websocket_manager
from app.timezone_utils import format_datetime

router = APIRouter(prefix="/api/logs", tags=["日志管理"])

class TaskLogResponse(BaseModel):
    id: int
    task_id: int
    task_name: str
    status: str
    start_time: str
    end_time: Optional[str]
    output: Optional[str]
    error_output: Optional[str]
    exit_code: Optional[int]

    class Config:
        from_attributes = True

    @classmethod
    def from_db_model(cls, log, db=None):
        """从数据库模型创建响应对象"""
        return cls(
            id=log.id,
            task_id=log.task_id,
            task_name=log.task_name,
            status=log.status,
            start_time=format_datetime(log.start_time, db) if log.start_time else "",
            end_time=format_datetime(log.end_time, db) if log.end_time else None,
            output=log.output,
            error_output=log.error_output,
            exit_code=log.exit_code
        )

class PaginatedLogsResponse(BaseModel):
    items: List[TaskLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

@router.get("/", response_model=PaginatedLogsResponse)
async def get_logs(
    task_id: Optional[int] = Query(None, description="任务ID过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    limit: int = Query(20, description="每页记录数"),
    offset: int = Query(0, description="偏移量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取任务执行日志（分页）"""
    query = db.query(TaskLog)

    # 应用过滤条件
    if task_id:
        query = query.filter(TaskLog.task_id == task_id)

    if status:
        query = query.filter(TaskLog.status == status)

    # 获取总数
    total = query.count()

    # 按开始时间倒序排列
    query = query.order_by(desc(TaskLog.start_time))

    # 应用分页
    logs = query.offset(offset).limit(limit).all()

    # 计算分页信息
    page = (offset // limit) + 1
    total_pages = (total + limit - 1) // limit

    items = [TaskLogResponse.from_db_model(log, db) for log in logs]

    return PaginatedLogsResponse(
        items=items,
        total=total,
        page=page,
        page_size=limit,
        total_pages=total_pages
    )

@router.get("/{log_id}", response_model=TaskLogResponse)
async def get_log(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取单个日志详情"""
    log = db.query(TaskLog).filter(TaskLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    
    return TaskLogResponse.from_db_model(log, db)

@router.delete("/{log_id}")
async def delete_log(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除单个日志"""
    log = db.query(TaskLog).filter(TaskLog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    
    db.delete(log)
    db.commit()
    
    return {"message": "日志已删除"}

@router.delete("/")
async def clear_logs(
    task_id: Optional[int] = Query(None, description="任务ID过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除筛选的日志"""
    query = db.query(TaskLog)

    # 应用过滤条件
    if task_id:
        query = query.filter(TaskLog.task_id == task_id)

    if status:
        query = query.filter(TaskLog.status == status)

    # 构建消息
    if task_id and status:
        message = f"任务 {task_id} 状态为 {status} 的日志已删除"
    elif task_id:
        message = f"任务 {task_id} 的日志已删除"
    elif status:
        message = f"状态为 {status} 的日志已删除"
    else:
        message = "所有日志已删除"

    deleted_count = query.count()
    query.delete()
    db.commit()

    return {"message": message, "deleted_count": deleted_count}

@router.get("/running/{task_id}")
async def get_running_task_log(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取正在运行任务的日志"""
    # 获取该任务最新的运行中日志
    log = db.query(TaskLog).filter(
        TaskLog.task_id == task_id,
        TaskLog.status == "running"
    ).order_by(desc(TaskLog.start_time)).first()

    if not log:
        raise HTTPException(status_code=404, detail="未找到正在运行的任务日志")

    # 创建响应对象并处理特殊的output字段
    response = TaskLogResponse.from_db_model(log, db)
    if not response.output:
        response.output = "任务正在运行中..."
    return response

@router.websocket("/ws/{task_id}")
async def websocket_task_log(websocket: WebSocket, task_id: int):
    """WebSocket连接用于实时日志传输"""
    room_id = f"task_{task_id}"
    await websocket_manager.connect(websocket, room_id)

    try:
        # 发送历史日志（如果任务正在运行或刚完成）
        from app.scheduler import task_scheduler

        # 获取任务的日志缓存
        log_cache = task_scheduler.get_task_log_cache(task_id)

        if log_cache:
            print(f"发送任务 {task_id} 的历史日志，输出行数: {len(log_cache.get('output_lines', []))}, 错误行数: {len(log_cache.get('error_lines', []))}")

            # 发送历史的stdout输出
            for line in log_cache.get("output_lines", []):
                await websocket_manager.send_personal_message({
                    "type": "task_output",
                    "task_id": task_id,
                    "log_id": log_cache.get("log_id"),
                    "output_line": line,
                    "output_type": "stdout"
                }, websocket)
                # 添加小延迟确保消息顺序
                await asyncio.sleep(0.01)

            # 发送历史的stderr输出
            for line in log_cache.get("error_lines", []):
                await websocket_manager.send_personal_message({
                    "type": "task_output",
                    "task_id": task_id,
                    "log_id": log_cache.get("log_id"),
                    "output_line": line,
                    "output_type": "stderr"
                }, websocket)
                # 添加小延迟确保消息顺序
                await asyncio.sleep(0.01)
        else:
            print(f"任务 {task_id} 没有找到日志缓存")

        while True:
            # 保持连接活跃
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, room_id)

@router.get("/stream/{task_id}")
async def stream_task_log(task_id: int, current_user: User = Depends(get_current_user)):
    """实时流式传输任务日志"""
    from fastapi.responses import StreamingResponse
    import asyncio
    import os
    import json

    async def generate_log_stream():
        log_file = f"logs/task_{task_id}_current.log"
        position = 0

        # 发送初始消息
        yield f"data: {json.dumps({'type': 'connected', 'task_id': task_id})}\n\n"

        while True:
            try:
                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8') as f:
                        f.seek(position)
                        new_content = f.read()
                        if new_content:
                            lines = new_content.split('\n')
                            for line in lines:
                                if line.strip():
                                    yield f"data: {json.dumps({'type': 'output', 'line': line})}\n\n"
                            position = f.tell()

                # 检查任务是否还在运行
                from app.scheduler import task_scheduler
                if task_id not in task_scheduler.running_tasks:
                    # 任务已完成，发送完成消息
                    yield f"data: {json.dumps({'type': 'completed'})}\n\n"
                    break

                await asyncio.sleep(0.5)  # 每0.5秒检查一次

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                break

    return StreamingResponse(
        generate_log_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

@router.get("/stats/summary")
async def get_log_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取日志统计信息"""
    from datetime import datetime, date

    # 今日开始时间
    today_start = datetime.combine(date.today(), datetime.min.time())

    # 总统计
    total_logs = db.query(TaskLog).count()
    success_logs = db.query(TaskLog).filter(TaskLog.status == "success").count()
    failed_logs = db.query(TaskLog).filter(TaskLog.status == "failed").count()
    running_logs = db.query(TaskLog).filter(TaskLog.status == "running").count()

    # 今日统计
    today_total = db.query(TaskLog).filter(TaskLog.start_time >= today_start).count()
    today_failed = db.query(TaskLog).filter(
        TaskLog.start_time >= today_start,
        TaskLog.status == "failed"
    ).count()

    return {
        "total": today_total,  # 改为今日执行总数
        "success": success_logs,
        "failed": today_failed,  # 改为今日失败数
        "running": running_logs,
        "success_rate": round(success_logs / total_logs * 100, 2) if total_logs > 0 else 0
    }

@router.post("/clear-all")
async def clear_all_logs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """清空所有日志（系统设置页面使用）"""
    deleted_count = db.query(TaskLog).count()
    db.query(TaskLog).delete()
    db.commit()

    return {"message": "所有日志已清空", "deleted_count": deleted_count}
