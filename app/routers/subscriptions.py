"""
脚本订阅管理路由
"""
import os
import stat
import hashlib
import shutil
import subprocess
import asyncio
import fnmatch
import re
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.auth import get_current_user
from app.models import User, ScriptSubscription, SubscriptionFile, SubscriptionLog, NotificationConfig
from app.scheduler import task_scheduler
from app.notification_service import notification_service
from app.routers.settings import get_system_config, set_system_config
from app.websocket_manager import websocket_manager

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])

# Pydantic模型
class SubscriptionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    git_url: str
    save_directory: str
    file_extensions: List[str] = []
    exclude_patterns: List[str] = []
    include_folders: bool = True
    include_subfolders: bool = True
    use_proxy: bool = False
    sync_delete_removed_files: bool = False
    cron_expression: str
    notification_enabled: bool = False
    notification_type: Optional[str] = None
    auto_create_tasks: bool = False

class SubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    git_url: Optional[str] = None
    save_directory: Optional[str] = None
    file_extensions: Optional[List[str]] = None
    exclude_patterns: Optional[List[str]] = None
    include_folders: Optional[bool] = None
    include_subfolders: Optional[bool] = None
    use_proxy: Optional[bool] = None
    sync_delete_removed_files: Optional[bool] = None
    cron_expression: Optional[str] = None
    notification_enabled: Optional[bool] = None
    notification_type: Optional[str] = None
    auto_create_tasks: Optional[bool] = None
    is_active: Optional[bool] = None

class SubscriptionResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    git_url: str
    save_directory: str
    file_extensions: List[str]
    exclude_patterns: List[str]
    include_folders: bool
    include_subfolders: bool
    use_proxy: bool
    sync_delete_removed_files: bool
    cron_expression: str
    notification_enabled: bool
    notification_type: Optional[str]
    auto_create_tasks: bool
    is_active: bool
    last_sync_time: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    has_requirements: Optional[bool] = None

class ProxyConfig(BaseModel):
    enabled: bool = False
    host: str = ""
    port: int = 0

class SubscriptionLogResponse(BaseModel):
    id: int
    subscription_id: int
    subscription_name: str
    status: str
    message: Optional[str]
    files_updated: int
    files_added: int
    start_time: datetime
    end_time: Optional[datetime]

# 全局代理配置缓存
proxy_config = ProxyConfig()

def extract_module_docstring(file_path: str) -> Optional[str]:
    """提取Python脚本的模块级文档字符串"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 使用正则表达式匹配模块级别的三引号文档字符串
        # 匹配模式：开头是可选的空白和注释，然后是三引号，接着是内容，最后是结束的三引号
        pattern = r'^(?:\s*#.*?\n)*\s*"""(.*?)"""'
        match = re.search(pattern, content, re.DOTALL)

        if match:
            # 返回匹配到的文档字符串内容，去除前后空白
            return match.group(1).strip()
        return None
    except Exception as e:
        print(f"提取文档字符串失败 {file_path}: {str(e)}")
        return None

def format_docstring_for_notification(docstring: str, max_length: int = 500) -> str:
    """格式化文档字符串用于通知显示"""
    if not docstring:
        return ""

    # 如果文档字符串太长，截断并添加省略号
    if len(docstring) > max_length:
        # 尝试在合适的位置截断（如换行符或句号）
        truncated = docstring[:max_length]
        last_newline = truncated.rfind('\n')
        last_period = truncated.rfind('。')
        last_dot = truncated.rfind('.')

        # 选择最合适的截断位置
        cut_pos = max(last_newline, last_period, last_dot)
        if cut_pos > max_length * 0.8:  # 如果截断位置不会丢失太多内容
            docstring = docstring[:cut_pos + 1] + "..."
        else:
            docstring = truncated + "..."

    # 保持原有的换行格式，但限制每行长度
    lines = docstring.split('\n')
    formatted_lines = []
    for line in lines:
        line = line.strip()
        if line:
            # 如果单行太长，进行换行
            if len(line) > 80:
                words = line.split(' ')
                current_line = ""
                for word in words:
                    if len(current_line + word) > 80:
                        if current_line:
                            formatted_lines.append(current_line.strip())
                            current_line = word + " "
                        else:
                            formatted_lines.append(word)
                            current_line = ""
                    else:
                        current_line += word + " "
                if current_line.strip():
                    formatted_lines.append(current_line.strip())
            else:
                formatted_lines.append(line)

    return '\n    '.join(formatted_lines)

def load_proxy_config_from_db(db: Session) -> ProxyConfig:
    """从数据库加载代理配置"""
    enabled = get_system_config(db, "proxy_enabled", "false") == "true"
    host = get_system_config(db, "proxy_host", "")
    port = int(get_system_config(db, "proxy_port", "0"))
    return ProxyConfig(enabled=enabled, host=host, port=port)

def save_proxy_config_to_db(db: Session, config: ProxyConfig):
    """保存代理配置到数据库"""
    set_system_config(db, "proxy_enabled", str(config.enabled).lower(), "代理是否启用")
    set_system_config(db, "proxy_host", config.host, "代理主机地址")
    set_system_config(db, "proxy_port", str(config.port), "代理端口")

@router.get("/proxy", response_model=ProxyConfig)
async def get_proxy_config(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """获取代理配置"""
    global proxy_config
    proxy_config = load_proxy_config_from_db(db)
    return proxy_config

@router.post("/proxy")
async def update_proxy_config(config: ProxyConfig, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """更新代理配置"""
    global proxy_config
    proxy_config = config
    save_proxy_config_to_db(db, config)
    return {"message": "代理配置已更新"}

@router.get("/", response_model=List[SubscriptionResponse])
async def get_subscriptions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取订阅列表"""
    subscriptions = db.query(ScriptSubscription).offset(skip).limit(limit).all()

    # 检查每个订阅是否包含requirements.txt文件
    scripts_dir = os.path.abspath("scripts")
    result = []
    for subscription in subscriptions:
        subscription_dict = {
            "id": subscription.id,
            "name": subscription.name,
            "description": subscription.description,
            "git_url": subscription.git_url,
            "save_directory": subscription.save_directory,
            "file_extensions": subscription.file_extensions or [],
            "exclude_patterns": subscription.exclude_patterns or [],
            "include_folders": subscription.include_folders,
            "include_subfolders": subscription.include_subfolders,
            "use_proxy": subscription.use_proxy,
            "sync_delete_removed_files": subscription.sync_delete_removed_files,
            "cron_expression": subscription.cron_expression,
            "notification_enabled": subscription.notification_enabled,
            "notification_type": subscription.notification_type,
            "auto_create_tasks": getattr(subscription, 'auto_create_tasks', False),
            "is_active": subscription.is_active,
            "last_sync_time": subscription.last_sync_time,
            "created_at": subscription.created_at,
            "updated_at": subscription.updated_at
        }

        # 检查是否存在requirements.txt文件
        repo_dir = os.path.join(scripts_dir, str(subscription.save_directory))
        requirements_file = os.path.join(repo_dir, "requirements.txt")
        subscription_dict["has_requirements"] = os.path.exists(requirements_file)

        result.append(subscription_dict)

    return result

@router.post("/", response_model=SubscriptionResponse)
async def create_subscription(
    subscription: SubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建订阅"""
    # 验证保存目录必须在scripts目录下
    scripts_dir = os.path.abspath("scripts")
    save_path = os.path.abspath(os.path.join(scripts_dir, subscription.save_directory.lstrip("/")))
    
    if not save_path.startswith(scripts_dir):
        raise HTTPException(status_code=400, detail="保存目录必须在scripts目录下")
    
    # 如果没有指定保存目录，根据Git URL自动生成
    if not subscription.save_directory:
        repo_name = subscription.git_url.split("/")[-1].replace(".git", "")
        subscription.save_directory = repo_name
    
    # 创建订阅记录
    db_subscription = ScriptSubscription(**subscription.dict())
    db.add(db_subscription)
    db.commit()
    db.refresh(db_subscription)
    
    # 添加到调度器
    if db_subscription.is_active:
        task_scheduler.add_subscription(db_subscription)
    
    return db_subscription

@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取单个订阅"""
    subscription = db.query(ScriptSubscription).filter(ScriptSubscription.id == subscription_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="订阅不存在")
    return subscription

@router.put("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: int,
    subscription_update: SubscriptionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新订阅"""
    subscription = db.query(ScriptSubscription).filter(ScriptSubscription.id == subscription_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="订阅不存在")
    
    # 更新字段
    update_data = subscription_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(subscription, field, value)
    
    subscription.updated_at = datetime.now()
    db.commit()
    db.refresh(subscription)
    
    # 更新调度器
    if subscription.is_active:
        task_scheduler.add_subscription(subscription)
    else:
        task_scheduler.remove_subscription(subscription.id)
    
    return subscription

@router.delete("/{subscription_id}")
async def delete_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除订阅"""
    subscription = db.query(ScriptSubscription).filter(ScriptSubscription.id == subscription_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="订阅不存在")
    
    # 从调度器移除
    task_scheduler.remove_subscription(subscription_id)
    
    # 删除相关文件记录
    db.query(SubscriptionFile).filter(SubscriptionFile.subscription_id == subscription_id).delete()
    
    # 删除订阅记录
    db.delete(subscription)
    db.commit()
    
    return {"message": "订阅已删除"}

@router.post("/{subscription_id}/sync")
async def sync_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """手动同步订阅"""
    subscription = db.query(ScriptSubscription).filter(ScriptSubscription.id == subscription_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="订阅不存在")
    
    # 执行同步
    await execute_subscription_sync(subscription_id, db)
    
    return {"message": "同步已开始"}

@router.get("/{subscription_id}/logs", response_model=List[SubscriptionLogResponse])
async def get_subscription_logs(
    subscription_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取订阅日志"""
    logs = db.query(SubscriptionLog).filter(
        SubscriptionLog.subscription_id == subscription_id
    ).order_by(SubscriptionLog.start_time.desc()).offset(skip).limit(limit).all()
    
    return logs

# 同步执行函数
async def execute_subscription_sync(subscription_id: int, db: Session = None):
    """执行订阅同步"""
    if db is None:
        from app.database import SessionLocal
        db = SessionLocal()
        should_close_db = True
    else:
        should_close_db = False
    
    try:
        subscription = db.query(ScriptSubscription).filter(ScriptSubscription.id == subscription_id).first()
        if not subscription:
            return
        
        # 创建日志记录
        log = SubscriptionLog(
            subscription_id=subscription.id,
            subscription_name=subscription.name,
            status="running",
            start_time=datetime.now()
        )
        db.add(log)
        db.commit()

        # 发送同步开始的WebSocket消息
        await websocket_manager.broadcast({
            "type": "subscription_sync_start",
            "subscription_id": subscription.id,
            "subscription_name": subscription.name,
            "log_id": log.id
        }, "global")

        try:
            # 执行Git同步
            updated_files, new_files, deleted_files = sync_git_repository(subscription, db)

            # 更新日志
            log.status = "success"
            log.files_updated = len(updated_files)
            log.files_added = len(new_files)

            # 构建日志消息
            message_parts = []
            if updated_files:
                message_parts.append(f"更新 {len(updated_files)} 个文件")
            if new_files:
                message_parts.append(f"新增 {len(new_files)} 个文件")
            if deleted_files:
                message_parts.append(f"删除 {len(deleted_files)} 个文件")

            log.message = f"同步成功，{', '.join(message_parts) if message_parts else '无变化'}"
            log.end_time = datetime.now()

            # 更新订阅的最后同步时间
            subscription.last_sync_time = datetime.now()

            db.commit()

            # 发送同步成功的WebSocket消息
            await websocket_manager.broadcast({
                "type": "subscription_sync_complete",
                "subscription_id": subscription.id,
                "subscription_name": subscription.name,
                "log_id": log.id,
                "status": "success",
                "files_updated": len(updated_files),
                "files_added": len(new_files),
                "message": log.message
            }, "global")

            # 发送通知
            if subscription.notification_enabled and (updated_files or new_files or deleted_files):
                # 构建repo_dir路径
                scripts_dir = os.path.abspath("scripts")
                repo_dir = os.path.join(scripts_dir, subscription.save_directory)
                await send_subscription_notification(subscription, updated_files, new_files, deleted_files, db, repo_dir)

        except Exception as e:
            log.status = "error"
            log.message = f"同步失败: {str(e)}"
            log.end_time = datetime.now()
            db.commit()

            # 发送同步失败的WebSocket消息
            await websocket_manager.broadcast({
                "type": "subscription_sync_complete",
                "subscription_id": subscription.id,
                "subscription_name": subscription.name,
                "log_id": log.id,
                "status": "error",
                "files_updated": 0,
                "files_added": 0,
                "message": log.message
            }, "global")

            raise
            
    finally:
        if should_close_db:
            db.close()

def sync_git_repository(subscription: ScriptSubscription, db: Session):
    """同步Git仓库"""
    scripts_dir = os.path.abspath("scripts")
    repo_dir = os.path.join(scripts_dir, subscription.save_directory)

    # 重新加载代理配置
    current_proxy_config = load_proxy_config_from_db(db)

    # 准备Git命令环境
    env = os.environ.copy()
    if subscription.use_proxy and current_proxy_config.enabled:
        proxy_url = f"http://{current_proxy_config.host}:{current_proxy_config.port}"
        env["http_proxy"] = proxy_url
        env["https_proxy"] = proxy_url
        print(f"使用代理: {proxy_url}")

    import subprocess
    import shutil

    # 检查目录是否存在且是Git仓库
    git_dir = os.path.join(repo_dir, '.git')
    is_git_repo = os.path.exists(git_dir)

    print(f"检查Git仓库状态:")
    print(f"  仓库目录: {repo_dir}")
    print(f"  .git目录: {git_dir}")
    print(f"  目录存在: {os.path.exists(repo_dir)}")
    print(f"  是Git仓库: {is_git_repo}")

    if is_git_repo:
        # 更新现有仓库
        print(f"更新现有仓库: {repo_dir}")
        try:
            # 先尝试获取当前分支
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                timeout=30
            )

            current_branch = result.stdout.strip() if result.returncode == 0 else "main"
            if not current_branch:
                current_branch = "main"

            print(f"当前分支: {current_branch}")

            # 执行pull命令
            cmd = ["git", "pull", "origin", current_branch]
            cwd = repo_dir

        except Exception as e:
            print(f"获取分支信息失败，使用默认pull: {e}")
            cmd = ["git", "pull"]
            cwd = repo_dir
    else:
        # 克隆新仓库
        print(f"克隆新仓库到: {repo_dir}")
        if os.path.exists(repo_dir):
            # 如果目录存在但不是Git仓库，先删除
            print(f"删除现有目录: {repo_dir}")
            shutil.rmtree(repo_dir)

        os.makedirs(repo_dir, exist_ok=True)
        cmd = ["git", "clone", subscription.git_url, "."]
        cwd = repo_dir

    # 执行Git命令
    try:
        print(f"执行命令: {' '.join(cmd)} (工作目录: {cwd})")
        result = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )

        print(f"Git命令输出: {result.stdout}")
        if result.stderr:
            print(f"Git命令错误输出: {result.stderr}")

        if result.returncode != 0:
            raise Exception(f"Git命令执行失败 (返回码: {result.returncode}): {result.stderr}")

    except subprocess.TimeoutExpired:
        raise Exception("Git命令执行超时")
    except Exception as e:
        raise Exception(f"Git命令执行失败: {str(e)}")

    # 在扫描文件变化之前，删除被排除的文件夹
    cleanup_excluded_paths(subscription, repo_dir)

    # 扫描文件变化
    return scan_file_changes(subscription, repo_dir, db)

def cleanup_excluded_paths(subscription: ScriptSubscription, repo_dir: str):
    """清理被排除的文件和文件夹"""
    exclude_patterns = getattr(subscription, 'exclude_patterns', None) or []
    if not exclude_patterns:
        return

    import shutil
    # 避免循环导入，直接实现force_remove_tree功能
    def force_remove_readonly(func, path, exc):
        if os.path.exists(path):
            os.chmod(path, stat.S_IWRITE)
            func(path)

    def force_remove_tree(path):
        try:
            shutil.rmtree(path)
        except (OSError, PermissionError):
            shutil.rmtree(path, onerror=force_remove_readonly)

    # 遍历仓库根目录，删除匹配排除模式的文件和文件夹
    for item in os.listdir(repo_dir):
        item_path = os.path.join(repo_dir, item)

        # 检查是否应该被排除
        if should_exclude_path(item, exclude_patterns):
            try:
                if os.path.isdir(item_path):
                    print(f"删除被排除的文件夹: {item}")
                    force_remove_tree(item_path)
                else:
                    print(f"删除被排除的文件: {item}")
                    # 处理只读文件
                    if os.path.exists(item_path):
                        os.chmod(item_path, stat.S_IWRITE)
                    os.remove(item_path)
            except Exception as e:
                print(f"删除被排除的路径失败 {item}: {e}")

def should_exclude_path(path: str, exclude_patterns: List[str]) -> bool:
    """检查路径是否应该被排除"""
    if not exclude_patterns:
        return False

    # 获取路径的各个部分
    path_parts = path.replace('\\', '/').split('/')

    for pattern in exclude_patterns:
        pattern = pattern.strip()
        if not pattern:
            continue

        # 检查完整路径匹配
        if fnmatch.fnmatch(path.replace('\\', '/'), pattern):
            return True

        # 检查路径中的任何部分是否匹配
        for part in path_parts:
            if fnmatch.fnmatch(part, pattern):
                return True

        # 检查文件名匹配
        filename = os.path.basename(path)
        if fnmatch.fnmatch(filename, pattern):
            return True

    return False

def scan_file_changes(subscription: ScriptSubscription, repo_dir: str, db: Session):
    """扫描文件变化"""
    updated_files = []
    new_files = []
    deleted_files = []

    # 获取现有文件记录
    existing_files = {f.file_path: f for f in db.query(SubscriptionFile).filter(
        SubscriptionFile.subscription_id == subscription.id
    ).all()}

    # 记录当前扫描到的文件
    current_files = set()

    # 获取排除模式
    exclude_patterns = getattr(subscription, 'exclude_patterns', None) or []

    # 扫描目录
    for root, dirs, files in os.walk(repo_dir):
        # 过滤文件夹
        if not getattr(subscription, 'include_subfolders', True) and root != repo_dir:
            continue

        # 检查当前目录是否应该被排除
        relative_root = os.path.relpath(root, repo_dir)
        if relative_root != '.' and should_exclude_path(relative_root, exclude_patterns):
            dirs.clear()  # 不进入被排除的目录
            continue

        # 过滤要进入的子目录
        dirs[:] = [d for d in dirs if not should_exclude_path(os.path.join(relative_root, d) if relative_root != '.' else d, exclude_patterns)]

        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, repo_dir)

            # 检查文件是否应该被排除
            if should_exclude_path(relative_path, exclude_patterns):
                continue

            # 检查文件扩展名
            file_extensions = getattr(subscription, 'file_extensions', None) or []
            if file_extensions:
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext not in file_extensions:
                    continue

            # 计算MD5
            file_md5 = calculate_file_md5(file_path)
            file_size = os.path.getsize(file_path)

            # 记录当前文件
            current_files.add(relative_path)

            if relative_path in existing_files:
                # 检查文件是否有更新
                existing_file = existing_files[relative_path]
                if existing_file.file_md5 != file_md5:
                    existing_file.file_md5 = file_md5
                    existing_file.file_size = file_size
                    existing_file.is_new = False
                    existing_file.updated_at = datetime.now()
                    updated_files.append(relative_path)
            else:
                # 新文件
                new_file = SubscriptionFile(
                    subscription_id=subscription.id,
                    file_path=relative_path,
                    file_md5=file_md5,
                    file_size=file_size,
                    is_new=True
                )
                db.add(new_file)
                new_files.append(relative_path)

    # 检查是否有文件被删除
    if getattr(subscription, 'sync_delete_removed_files', False):
        for file_path, file_record in existing_files.items():
            if file_path not in current_files:
                # 文件在Git仓库中被删除，同步删除本地文件
                local_file_path = os.path.join(repo_dir, file_path)
                if os.path.exists(local_file_path):
                    try:
                        os.remove(local_file_path)
                        deleted_files.append(file_path)
                        print(f"删除本地文件: {local_file_path}")
                    except Exception as e:
                        print(f"删除文件失败 {local_file_path}: {e}")

                # 从数据库中删除文件记录
                db.delete(file_record)

    db.commit()

    # 如果启用了自动创建任务，处理新增的脚本文件
    if getattr(subscription, 'auto_create_tasks', False):
        auto_create_tasks_for_scripts(subscription, new_files, repo_dir, db)

    return updated_files, new_files, deleted_files

def auto_create_tasks_for_scripts(subscription: ScriptSubscription, new_files: List[str], repo_dir: str, db: Session):
    """为新增的Python和JavaScript脚本自动创建任务"""
    from app.models import Task

    for file_path in new_files:
        # 处理Python和JavaScript脚本
        script_type = None
        if file_path.endswith('.py'):
            script_type = "python"
        elif file_path.endswith('.js'):
            script_type = "nodejs"
        else:
            continue  # 跳过其他类型的文件

        # 构建脚本路径（相对于scripts目录）
        # 由于任务执行时工作目录已经是scripts目录，所以这里不需要包含"scripts"前缀
        full_script_path = os.path.join(str(subscription.save_directory), file_path)
        absolute_script_path = os.path.join(repo_dir, file_path)

        # 检查文件是否存在
        if not os.path.exists(absolute_script_path):
            continue

        # 提取文件名作为任务名（去掉扩展名）
        script_name = os.path.splitext(os.path.basename(file_path))[0]
        task_name = f"{subscription.name}_{script_name}"

        # 检查任务名是否已存在
        existing_task = db.query(Task).filter(Task.name == task_name).first()
        if existing_task:
            print(f"任务 {task_name} 已存在，跳过创建")
            continue

        # 创建新任务
        try:
            new_task = Task(
                name=task_name,
                description=f"由订阅 {subscription.name} 自动创建的{script_type}任务",
                script_path=full_script_path,
                script_type=script_type,
                cron_expression="0 3 * * *",  # 每天凌晨3点执行
                environment_vars={},
                group_name=f"订阅_{subscription.name}",
                is_active=True
            )

            db.add(new_task)
            db.commit()
            db.refresh(new_task)

            # 添加到调度器
            from app.scheduler import task_scheduler
            task_scheduler.add_task(new_task)

            print(f"自动创建{script_type}任务成功: {task_name}")

        except Exception as e:
            print(f"自动创建任务失败 {task_name}: {str(e)}")
            db.rollback()

def calculate_file_md5(file_path: str) -> str:
    """计算文件MD5值"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

async def send_subscription_notification(subscription: ScriptSubscription, updated_files: List[str], new_files: List[str], deleted_files: List[str], db: Session, repo_dir: str = None):
    """发送订阅通知"""
    notification_type = getattr(subscription, 'notification_type', None)
    if not notification_type:
        return

    # 获取通知配置
    notification_config = db.query(NotificationConfig).filter(
        NotificationConfig.name == subscription.notification_type,
        NotificationConfig.is_active == True
    ).first()

    if not notification_config:
        return

    # 构建通知内容
    title = f"脚本订阅更新通知 - {subscription.name}"
    content_lines = [f"订阅 {subscription.name} 有更新："]

    if new_files:
        content_lines.append(f"\n新增文件 ({len(new_files)} 个):")
        for file in new_files[:10]:  # 最多显示10个
            content_lines.append(f"  + {file}")

            # 如果是Python脚本且提供了repo_dir，尝试提取文档字符串
            if file.endswith('.py') and repo_dir:
                script_path = os.path.join(repo_dir, file)
                docstring = extract_module_docstring(script_path)
                if docstring:
                    # 格式化文档字符串，限制长度并保持格式
                    formatted_docstring = format_docstring_for_notification(docstring)
                    content_lines.append(f"    📝 脚本说明:")
                    content_lines.append(f"    {formatted_docstring}")

        if len(new_files) > 10:
            content_lines.append(f"  ... 还有 {len(new_files) - 10} 个文件")

    if updated_files:
        content_lines.append(f"\n更新文件 ({len(updated_files)} 个):")
        for file in updated_files[:10]:  # 最多显示10个
            content_lines.append(f"  * {file}")

            # 如果是Python脚本且提供了repo_dir，尝试提取文档字符串
            if file.endswith('.py') and repo_dir:
                script_path = os.path.join(repo_dir, file)
                docstring = extract_module_docstring(script_path)
                if docstring:
                    # 格式化文档字符串，限制长度并保持格式
                    formatted_docstring = format_docstring_for_notification(docstring)
                    content_lines.append(f"    📝 脚本说明:")
                    content_lines.append(f"    {formatted_docstring}")

        if len(updated_files) > 10:
            content_lines.append(f"  ... 还有 {len(updated_files) - 10} 个文件")

    if deleted_files:
        content_lines.append(f"\n删除文件 ({len(deleted_files)} 个):")
        for file in deleted_files[:10]:  # 最多显示10个
            content_lines.append(f"  - {file}")
        if len(deleted_files) > 10:
            content_lines.append(f"  ... 还有 {len(deleted_files) - 10} 个文件")

    content = "\n".join(content_lines)

    # 发送通知
    await notification_service.send_notification(notification_config, title, content)

def compare_versions(installed_version: str, required_version: str, operator: str) -> str:
    """比较版本号并返回状态文本"""
    def parse_version(version_str):
        """解析版本号为数字列表"""
        # 移除非数字和点的字符，然后分割
        clean_version = ''.join(c if c.isdigit() or c == '.' else '' for c in version_str)
        parts = clean_version.split('.')
        return [int(part) if part.isdigit() else 0 for part in parts if part]

    try:
        installed_parts = parse_version(installed_version)
        required_parts = parse_version(required_version)

        # 补齐版本号长度
        max_len = max(len(installed_parts), len(required_parts))
        installed_parts.extend([0] * (max_len - len(installed_parts)))
        required_parts.extend([0] * (max_len - len(required_parts)))

        # 比较版本号
        def compare_version_lists(v1, v2):
            for i in range(len(v1)):
                if v1[i] > v2[i]:
                    return 1
                elif v1[i] < v2[i]:
                    return -1
            return 0

        comparison = compare_version_lists(installed_parts, required_parts)

        if operator == '==':
            return '版本相同' if comparison == 0 else ('需要降级' if comparison > 0 else '需要升级')
        elif operator == '>=':
            return '已安装' if comparison >= 0 else '需要升级'
        elif operator == '>':
            return '已安装' if comparison > 0 else '需要升级'
        elif operator == '<=':
            return '已安装' if comparison <= 0 else '需要降级'
        elif operator == '<':
            return '已安装' if comparison < 0 else '需要降级'
        elif operator == '!=':
            return '已安装' if comparison != 0 else '版本冲突'
        elif operator == '~=':
            # 兼容版本比较（主版本相同，次版本大于等于）
            if len(required_parts) >= 2:
                if installed_parts[0] == required_parts[0] and comparison >= 0:
                    return '已安装'
                else:
                    return '需要升级'
            else:
                return '已安装' if comparison >= 0 else '需要升级'
        else:
            return '已安装'

    except Exception as e:
        return f'版本比较失败: {str(e)}'

@router.get("/{subscription_id}/requirements")
async def check_requirements(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """检查订阅目录中的requirements.txt依赖"""
    subscription = db.query(ScriptSubscription).filter(ScriptSubscription.id == subscription_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="订阅不存在")

    # 构建订阅目录路径
    scripts_dir = os.path.abspath("scripts")
    repo_dir = os.path.join(scripts_dir, str(subscription.save_directory))
    requirements_file = os.path.join(repo_dir, "requirements.txt")

    if not os.path.exists(requirements_file):
        raise HTTPException(status_code=404, detail="未找到requirements.txt文件")

    try:
        # 读取requirements.txt内容
        with open(requirements_file, 'r', encoding='utf-8') as f:
            requirements_content = f.read()

        # 解析requirements.txt
        requirements = []
        for line in requirements_content.strip().split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                # 解析包名和版本要求，支持更多操作符
                package_name = line
                version = None
                operator = None

                # 按优先级检查操作符（长的先检查）
                operators = ['>=', '<=', '==', '!=', '~=', '>', '<']
                for op in operators:
                    if op in line:
                        parts = line.split(op, 1)
                        if len(parts) == 2:
                            package_name = parts[0].strip()
                            version = parts[1].strip()
                            operator = op
                            break

                # 处理复杂的版本要求（如 package>=1.0,<2.0）
                if ',' in line and operator:
                    # 暂时只取第一个条件，复杂条件后续可以扩展
                    pass

                requirements.append({
                    'name': package_name,
                    'required_version': version,
                    'operator': operator
                })

        # 检查每个包的安装状态
        result = []
        for req in requirements:
            package_name = req['name']
            required_version = req['required_version']

            # 检查Python包是否已安装
            try:
                check_result = subprocess.run(
                    ["pip", "show", package_name],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if check_result.returncode == 0:
                    # 解析pip show输出获取版本信息
                    output_lines = check_result.stdout.split('\n')
                    installed_version = None
                    for line in output_lines:
                        if line.startswith('Version:'):
                            installed_version = line.split(':', 1)[1].strip()
                            break

                    # 判断版本状态
                    status = 'installed'
                    status_text = '已安装'

                    if required_version and installed_version and req['operator']:
                        status_text = compare_versions(installed_version, required_version, req['operator'])
                    elif required_version and installed_version:
                        # 没有操作符时，默认使用==比较
                        status_text = compare_versions(installed_version, required_version, '==')

                    result.append({
                        'name': package_name,
                        'required_version': required_version,
                        'installed_version': installed_version,
                        'status': status,
                        'status_text': status_text,
                        'operator': req['operator']
                    })
                else:
                    result.append({
                        'name': package_name,
                        'required_version': required_version,
                        'installed_version': None,
                        'status': 'not_installed',
                        'status_text': '未安装',
                        'operator': req['operator']
                    })

            except subprocess.TimeoutExpired:
                result.append({
                    'name': package_name,
                    'required_version': required_version,
                    'installed_version': None,
                    'status': 'error',
                    'status_text': '检查超时',
                    'operator': req['operator']
                })
            except Exception as e:
                result.append({
                    'name': package_name,
                    'required_version': required_version,
                    'installed_version': None,
                    'status': 'error',
                    'status_text': f'检查失败: {str(e)}',
                    'operator': req['operator']
                })

        return {
            'subscription_name': subscription.name,
            'requirements_file': requirements_file,
            'requirements': result,
            'total_count': len(result),
            'installed_count': len([r for r in result if r['status'] == 'installed']),
            'not_installed_count': len([r for r in result if r['status'] == 'not_installed'])
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检查依赖失败: {str(e)}")
