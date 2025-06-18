"""
Pinchy - Python、Node.js脚本调度执行系统
主应用入口
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import create_tables, ensure_directories, get_db
from app.auth import init_admin_user, get_current_user
from app.scheduler import task_scheduler
from app.websocket_manager import websocket_manager
from app.models import User
from app.version import get_current_version

# 导入路由
from app.routers import auth, files, tasks, logs, env, packages, settings, notifications, api_debug, subscriptions

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print("正在启动 Pinchy 系统...")
    
    # 创建数据表
    create_tables()
    print("数据库表已创建")
    
    # 确保必要目录存在
    ensure_directories()
    print("必要目录已创建")
    
    # 初始化管理员用户、系统版本和系统UUID
    from app.database import SessionLocal
    from app.routers.settings import init_system_version, init_system_uuid, initialize_system_env_vars
    from app.routers.subscriptions import load_proxy_config_from_db, proxy_config
    db = SessionLocal()
    try:
        init_admin_user(db)
        init_system_version(db)
        init_system_uuid(db)
        # 初始化系统环境变量
        await initialize_system_env_vars(db)
        # 加载代理配置
        global_proxy_config = load_proxy_config_from_db(db)
        proxy_config.enabled = global_proxy_config.enabled
        proxy_config.host = global_proxy_config.host
        proxy_config.port = global_proxy_config.port
        print(f"已加载代理配置: enabled={proxy_config.enabled}")
    finally:
        db.close()
    
    # 启动任务调度器
    task_scheduler.start()
    
    # 从数据库加载任务
    task_scheduler.load_tasks_from_db()
    
    print("Pinchy 系统启动完成!")
    
    yield
    
    # 关闭时执行
    print("正在关闭 Pinchy 系统...")
    task_scheduler.shutdown()
    print("Pinchy 系统已关闭")

# 创建FastAPI应用
app = FastAPI(
    title="Pinchy",
    description="Python、Node.js脚本调度执行系统",
    version=get_current_version(),
    lifespan=lifespan
)

# 注册路由
app.include_router(auth.router)
app.include_router(files.router)
app.include_router(tasks.router)
app.include_router(logs.router)
app.include_router(env.router)
app.include_router(packages.router)
app.include_router(settings.router)
app.include_router(notifications.router)
app.include_router(api_debug.router)
app.include_router(subscriptions.router)

# 挂载静态文件
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_root():
    """返回主页"""
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    else:
        return {"message": "欢迎使用 Pinchy - Python、Node.js脚本调度执行系统"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点，用于实时日志推送"""
    await websocket_manager.connect(websocket, "global")
    try:
        while True:
            # 保持连接活跃
            data = await websocket.receive_text()
            # 可以在这里处理客户端发送的消息
            if data == "ping":
                await websocket_manager.send_personal_message({"type": "pong"}, websocket)
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, "global")

# @app.get("/api/health")
# async def health_check():
#     """健康检查端点"""
#     return {
#         "status": "healthy",
#         "message": "Pinchy 系统运行正常",
#         "scheduler_running": task_scheduler.scheduler.running,
#         "active_connections": websocket_manager.get_connection_count(),
#         "websocket_rooms": list(websocket_manager.active_connections.keys())
#     }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
