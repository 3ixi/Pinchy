# -*- coding: utf-8 -*-
"""
SendNotify.py - 通知发送模块
与Pinchy系统的通知服务集成，支持脚本通过 from SendNotify import send 进行推送
"""
import os
import sys
import asyncio
import json
import time
import hashlib
from typing import Optional, Dict

# 添加项目根目录到Python路径，以便导入app模块
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# 确保工作目录是项目根目录，这样可以找到数据库文件
original_cwd = os.getcwd()
if os.path.basename(os.getcwd()) == 'scripts':
    os.chdir(parent_dir)

# 重复通知检测缓存（内存中存储，避免短时间内重复发送相同通知）
_notification_cache: Dict[str, float] = {}
_CACHE_EXPIRE_SECONDS = 3  # 缓存过期时间（秒）

try:
    from app.database import SessionLocal
    from app.models import NotificationConfig, SystemConfig
    from app.notification_service import notification_service
    PINCHY_AVAILABLE = True
except ImportError as e:
    print(f"导入Pinchy系统模块失败: {e}")
    print("请确保此文件位于Pinchy系统的scripts目录下")
    PINCHY_AVAILABLE = False


def get_sendnotify_config() -> Optional[str]:
    """获取SendNotify配置的通知方式"""
    if not PINCHY_AVAILABLE:
        return None

    try:
        db = SessionLocal()
        try:
            config = db.query(SystemConfig).filter(
                SystemConfig.config_key == "sendnotify_notification_type"
            ).first()
            if config:
                return config.config_value
            return None
        finally:
            db.close()
    except Exception:
        # 静默处理数据库错误
        return None


def _generate_notification_key(title: str, content: str, notification_type: str) -> str:
    """生成通知的唯一标识键"""
    message = f"{title}|{content}|{notification_type}"
    return hashlib.md5(message.encode('utf-8')).hexdigest()


def _is_duplicate_notification(title: str, content: str, notification_type: str) -> bool:
    """检查是否为重复通知"""
    current_time = time.time()
    notification_key = _generate_notification_key(title, content, notification_type)

    # 清理过期的缓存项
    expired_keys = [key for key, timestamp in _notification_cache.items()
                   if current_time - timestamp > _CACHE_EXPIRE_SECONDS]
    for key in expired_keys:
        del _notification_cache[key]

    # 检查是否为重复通知
    if notification_key in _notification_cache:
        return True

    # 记录当前通知
    _notification_cache[notification_key] = current_time
    return False


def get_notification_config(notification_type: str) -> Optional[NotificationConfig]:
    """获取指定类型的通知配置"""
    if not PINCHY_AVAILABLE:
        return None

    try:
        db = SessionLocal()
        try:
            config = db.query(NotificationConfig).filter(
                NotificationConfig.name == notification_type,
                NotificationConfig.is_active == True
            ).first()
            return config
        finally:
            db.close()
    except Exception:
        # 静默处理数据库错误
        return None


async def send_notification_async(title: str, content: str) -> bool:
    """异步发送通知"""
    try:
        if not PINCHY_AVAILABLE:
            return False

        # 获取SendNotify配置的通知方式
        notification_type = get_sendnotify_config()
        if not notification_type:
            print("SendNotify未配置通知方式，请在通知服务页面配置")
            return False

        # 检查是否为重复通知
        if _is_duplicate_notification(title, content, notification_type):
            print(f"跳过重复通知: {title}")
            return True  # 返回True表示"成功"处理了重复通知

        # 获取对应的通知配置
        notification_config = get_notification_config(notification_type)
        if not notification_config:
            print(f"通知配置 {notification_type} 不存在或未激活")
            return False

        # 使用通知服务发送通知
        success = await notification_service.send_notification(
            notification_config, title, content
        )

        if success:
            print(f"通知发送成功: {title}")
        else:
            print(f"通知发送失败: {title}")

        return success

    except Exception as e:
        print(f"发送通知时出错: {e}")
        return False


def send(title: str, content: str = "") -> bool:
    """
    发送通知的主要接口函数
    
    Args:
        title (str): 通知标题
        content (str): 通知内容，可选
    
    Returns:
        bool: 发送是否成功
    """
    try:
        # 如果没有提供内容，使用标题作为内容
        if not content:
            content = title
        
        # 在新的事件循环中运行异步函数
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果当前已有事件循环在运行，创建新的线程来执行
                import threading
                import concurrent.futures
                
                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(send_notification_async(title, content))
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    return future.result(timeout=30)  # 30秒超时
            else:
                return loop.run_until_complete(send_notification_async(title, content))
        except RuntimeError:
            # 没有事件循环，创建新的
            return asyncio.run(send_notification_async(title, content))
            
    except Exception as e:
        print(f"SendNotify发送失败: {e}")
        return False


# 兼容性别名
def sendNotify(title: str, content: str = "") -> bool:
    """兼容性函数，与send功能相同"""
    return send(title, content)


if __name__ == "__main__":
    # 测试代码
    print("SendNotify模块测试")
    
    # 测试发送通知
    success = send("SendNotify测试", "这是一条来自SendNotify模块的测试消息")
    if success:
        print("✅ 测试通知发送成功")
    else:
        print("❌ 测试通知发送失败")
