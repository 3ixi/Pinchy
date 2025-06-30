"""
通知服务相关路由
"""
import aiohttp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.auth import get_current_user
from app.models import User, NotificationConfig, TaskNotificationConfig, Task, SystemConfig

router = APIRouter(prefix="/api/notifications", tags=["通知服务"])

# Pydantic 模型
class NotificationConfigCreate(BaseModel):
    name: str  # email, pushplus, wxpusher
    config: Dict[str, Any]

class TaskNotificationConfigCreate(BaseModel):
    task_id: int
    notification_type: Optional[str] = None
    error_only: bool = False
    keywords: Optional[str] = None

class TestNotificationRequest(BaseModel):
    config_id: int

class SendNotifyConfigRequest(BaseModel):
    notification_type: Optional[str] = None

@router.get("/configs")
async def get_notification_configs(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """获取所有通知配置"""
    configs = db.query(NotificationConfig).all()
    result = []
    for config in configs:
        result.append({
            "id": config.id,
            "name": config.name,
            "config": config.config,
            "is_active": config.is_active,
            "created_at": config.created_at.isoformat(),
            "updated_at": config.updated_at.isoformat() if config.updated_at else None
        })
    return result

@router.post("/configs")
async def create_notification_config(
    config_data: NotificationConfigCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """创建通知配置"""
    # 验证配置类型
    supported_types = ["email", "pushplus", "wxpusher", "telegram", "wecom", "wecom_app", "serverchan", "dingtalk", "bark"]
    if config_data.name not in supported_types:
        raise HTTPException(status_code=400, detail="不支持的通知类型")
    
    # 检查是否已存在同类型配置
    existing_config = db.query(NotificationConfig).filter(
        NotificationConfig.name == config_data.name
    ).first()
    if existing_config:
        raise HTTPException(status_code=400, detail=f"{config_data.name} 配置已存在")
    
    # 创建配置
    config = NotificationConfig(
        name=config_data.name,
        config=config_data.config,
        is_active=False  # 默认未激活，需要测试成功后激活
    )
    
    db.add(config)
    db.commit()
    db.refresh(config)
    
    return {
        "id": config.id,
        "name": config.name,
        "config": config.config,
        "is_active": config.is_active,
        "created_at": config.created_at.isoformat(),
        "updated_at": config.updated_at.isoformat() if config.updated_at else None
    }

@router.put("/configs/{config_id}")
async def update_notification_config(
    config_id: int,
    config_data: NotificationConfigCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """更新通知配置"""
    # 查找现有配置
    config = db.query(NotificationConfig).filter(
        NotificationConfig.id == config_id
    ).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")

    # 验证配置类型
    supported_types = ["email", "pushplus", "wxpusher", "telegram", "wecom", "wecom_app", "serverchan", "dingtalk", "bark"]
    if config_data.name not in supported_types:
        raise HTTPException(status_code=400, detail="不支持的通知类型")

    # 如果更改了通知类型，检查是否已存在同类型配置
    if config.name != config_data.name:
        existing_config = db.query(NotificationConfig).filter(
            NotificationConfig.name == config_data.name,
            NotificationConfig.id != config_id
        ).first()
        if existing_config:
            raise HTTPException(status_code=400, detail=f"{config_data.name} 配置已存在")

    # 更新配置
    config.name = config_data.name
    config.config = config_data.config
    config.is_active = False  # 更新后需要重新测试激活

    db.commit()
    db.refresh(config)

    return {
        "id": config.id,
        "name": config.name,
        "config": config.config,
        "is_active": config.is_active,
        "created_at": config.created_at.isoformat(),
        "updated_at": config.updated_at.isoformat() if config.updated_at else None
    }

@router.delete("/configs/{config_id}")
async def delete_notification_config(
    config_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """删除通知配置"""
    config = db.query(NotificationConfig).filter(
        NotificationConfig.id == config_id
    ).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")

    # 删除相关的任务通知配置
    db.query(TaskNotificationConfig).filter(
        TaskNotificationConfig.notification_type == config.name
    ).delete()

    # 删除通知配置
    db.delete(config)
    db.commit()

    return {"message": "配置删除成功"}

@router.post("/test")
async def test_notification(
    test_request: TestNotificationRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """测试通知配置"""
    config = db.query(NotificationConfig).filter(
        NotificationConfig.id == test_request.config_id
    ).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    try:
        # 发送测试通知
        success = await _send_test_notification(config.name, config.config)
        
        if success:
            # 测试成功，激活配置
            config.is_active = True
            db.commit()
            return {"message": "测试通知发送成功，配置已激活"}
        else:
            return {"message": "测试通知发送失败，请检查配置"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}")

@router.get("/task-configs")
async def get_task_notification_configs(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """获取所有任务通知配置"""
    configs = db.query(TaskNotificationConfig).all()
    result = []
    for config in configs:
        result.append({
            "id": config.id,
            "task_id": config.task_id,
            "notification_type": config.notification_type,
            "error_only": config.error_only,
            "keywords": config.keywords,
            "created_at": config.created_at.isoformat(),
            "updated_at": config.updated_at.isoformat() if config.updated_at else None
        })
    return result

@router.post("/task-configs")
async def create_task_notification_config(
    config_data: TaskNotificationConfigCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """创建或更新任务通知配置"""
    print(f"收到任务通知配置请求: {config_data}")
    print(f"task_id: {config_data.task_id}, type: {type(config_data.task_id)}")
    print(f"notification_type: {config_data.notification_type}, type: {type(config_data.notification_type)}")
    print(f"error_only: {config_data.error_only}, type: {type(config_data.error_only)}")
    print(f"keywords: {config_data.keywords}, type: {type(config_data.keywords)}")

    # 检查任务是否存在
    task = db.query(Task).filter(Task.id == config_data.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 检查通知类型是否有效且已激活
    if config_data.notification_type:
        notification_config = db.query(NotificationConfig).filter(
            NotificationConfig.name == config_data.notification_type,
            NotificationConfig.is_active == True
        ).first()
        if not notification_config:
            raise HTTPException(status_code=400, detail="通知类型无效或未激活")
    
    # 检查是否已存在配置
    existing_config = db.query(TaskNotificationConfig).filter(
        TaskNotificationConfig.task_id == config_data.task_id
    ).first()
    
    if existing_config:
        # 更新现有配置
        existing_config.notification_type = config_data.notification_type
        existing_config.error_only = config_data.error_only
        existing_config.keywords = config_data.keywords
        db.commit()
        db.refresh(existing_config)
        
        return {
            "id": existing_config.id,
            "task_id": existing_config.task_id,
            "notification_type": existing_config.notification_type,
            "error_only": existing_config.error_only,
            "keywords": existing_config.keywords,
            "created_at": existing_config.created_at.isoformat(),
            "updated_at": existing_config.updated_at.isoformat() if existing_config.updated_at else None
        }
    else:
        # 创建新配置
        config = TaskNotificationConfig(
            task_id=config_data.task_id,
            notification_type=config_data.notification_type,
            error_only=config_data.error_only,
            keywords=config_data.keywords
        )
        
        db.add(config)
        db.commit()
        db.refresh(config)
        
        return {
            "id": config.id,
            "task_id": config.task_id,
            "notification_type": config.notification_type,
            "error_only": config.error_only,
            "keywords": config.keywords,
            "created_at": config.created_at.isoformat(),
            "updated_at": config.updated_at.isoformat() if config.updated_at else None
        }

@router.get("/active-configs")
async def get_active_notification_configs(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """获取已激活的通知配置列表"""
    configs = db.query(NotificationConfig).filter(
        NotificationConfig.is_active == True
    ).all()

    return [
        {
            "id": config.id,
            "name": config.name,
            "config": config.config,
            "display_name": _get_display_name(config.name),
            "is_active": config.is_active,
            "created_at": config.created_at.isoformat(),
            "updated_at": config.updated_at.isoformat() if config.updated_at else None
        }
        for config in configs
    ]

def _get_display_name(config_name: str) -> str:
    """获取配置的显示名称"""
    display_names = {
        "email": "邮箱通知",
        "pushplus": "PushPlus",
        "wxpusher": "WxPusher",
        "telegram": "Telegram机器人",
        "wecom": "企微WebHook",
        "wecom_app": "企微应用通知",
        "serverchan": "Server酱",
        "dingtalk": "钉钉机器人",
        "bark": "Bark"
    }
    return display_names.get(config_name, config_name)

async def _send_test_notification(config_type: str, config: Dict[str, Any]) -> bool:
    """发送测试通知"""
    try:
        if config_type == "email":
            return await _send_test_email(config)
        elif config_type == "pushplus":
            return await _send_test_pushplus(config)
        elif config_type == "wxpusher":
            return await _send_test_wxpusher(config)
        elif config_type == "telegram":
            return await _send_test_telegram(config)
        elif config_type == "wecom":
            return await _send_test_wecom(config)
        elif config_type == "wecom_app":
            return await _send_test_wecom_app(config)
        elif config_type == "serverchan":
            return await _send_test_serverchan(config)
        elif config_type == "dingtalk":
            return await _send_test_dingtalk(config)
        elif config_type == "bark":
            return await _send_test_bark(config)
        else:
            print(f"不支持的通知类型: {config_type}")
            return False
    except Exception as e:
        print(f"发送测试通知失败: {e}")
        return False


async def _send_test_email(config: Dict[str, Any]) -> bool:
    """发送测试邮件通知"""
    try:
        # 邮件配置验证
        smtp_server = config.get("smtp_server")
        smtp_port = config.get("smtp_port", 587)
        username = config.get("username")
        password = config.get("password")
        to_email = config.get("to_email")

        if not all([smtp_server, username, password, to_email]):
            print("邮件配置不完整，缺少必要参数")
            return False

        # 创建测试邮件
        msg = MIMEMultipart()
        msg['From'] = username
        msg['To'] = to_email
        msg['Subject'] = "Pinchy系统 - 邮件通知测试"

        # 邮件内容
        test_content = f"""
📧 Pinchy系统邮件通知测试

✅ 如果您收到这封邮件，说明邮件通知配置成功！

📋 配置信息：
• SMTP服务器: {smtp_server}
• SMTP端口: {smtp_port}
• 发送邮箱: {username}
• 接收邮箱: {to_email}

⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎉 您现在可以正常接收任务执行通知了！
        """.strip()

        msg.attach(MIMEText(test_content, 'plain', 'utf-8'))

        # 发送邮件
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(msg)

        print(f"测试邮件发送成功: {username} -> {to_email}")
        return True

    except Exception as e:
        print(f"发送测试邮件失败: {e}")
        return False


async def _send_test_pushplus(config: Dict[str, Any]) -> bool:
    """发送测试PushPlus通知"""
    try:
        token = config.get("token")
        if not token:
            print("PushPlus token未配置")
            return False

        url = "http://www.pushplus.plus/send"

        # 构建测试消息
        title = "Pinchy系统 - PushPlus通知测试"
        content = f"""
📱 Pinchy系统PushPlus通知测试

✅ 如果您收到这条消息，说明PushPlus通知配置成功！

📋 配置信息：
• Token: {token[:8]}...{token[-8:] if len(token) > 16 else token}

⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎉 您现在可以正常接收任务执行通知了！
        """.strip()

        # 获取用户配置的模板类型，默认为txt
        template = config.get("template", "txt")

        data = {
            "token": token,
            "title": title,
            "content": content,
            "template": template
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, timeout=10) as response:
                result = await response.json()
                if result.get("code") == 200:
                    print(f"测试PushPlus通知发送成功: {result}")
                    return True
                else:
                    print(f"PushPlus发送失败: {result}")
                    return False

    except Exception as e:
        print(f"发送测试PushPlus通知失败: {e}")
        return False


async def _send_test_wxpusher(config: Dict[str, Any]) -> bool:
    """发送测试WxPusher通知"""
    try:
        app_token = config.get("app_token")
        uids = config.get("uids", [])

        if not app_token:
            print("WxPusher app_token未配置")
            return False

        if not uids or not isinstance(uids, list) or len(uids) == 0:
            print("WxPusher uids未配置或格式错误")
            return False

        url = "http://wxpusher.zjiecode.com/api/send/message"

        # 构建测试消息
        title = "Pinchy系统 - WxPusher通知测试"
        content = f"""
📱 Pinchy系统WxPusher通知测试

✅ 如果您收到这条消息，说明WxPusher通知配置成功！

📋 配置信息：
• AppToken: {app_token[:8]}...{app_token[-8:] if len(app_token) > 16 else app_token}
• 接收用户: {len(uids)}个

⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎉 您现在可以正常接收任务执行通知了！
        """.strip()

        # 获取用户配置的内容类型，默认为1（文本类型）
        content_type = config.get("content_type", 1)

        data = {
            "appToken": app_token,
            "content": content,
            "summary": title,
            "contentType": content_type,
            "uids": uids
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, timeout=10) as response:
                result = await response.json()
                if result.get("success"):
                    print(f"测试WxPusher通知发送成功: {result}")
                    return True
                else:
                    print(f"WxPusher发送失败: {result}")
                    return False

    except Exception as e:
        print(f"发送测试WxPusher通知失败: {e}")
        return False

# 通用通知发送函数
async def send_notification(notification_config: NotificationConfig, title: str, content: str) -> bool:
    """发送通知"""
    try:
        if notification_config.name == "email":
            return await _send_email_notification(notification_config.config, title, content)
        elif notification_config.name == "pushplus":
            return await _send_pushplus_notification(notification_config.config, title, content)
        elif notification_config.name == "wxpusher":
            return await _send_wxpusher_notification(notification_config.config, title, content)
        elif notification_config.name == "wecom":
            return await _send_wecom_notification(notification_config.config, title, content)
        elif notification_config.name == "wecom_app":
            return await _send_wecom_app_notification(notification_config.config, title, content)
        else:
            print(f"不支持的通知类型: {notification_config.name}")
            return False
    except Exception as e:
        print(f"发送通知失败: {e}")
        return False

async def _send_email_notification(config: Dict[str, Any], title: str, content: str) -> bool:
    """发送邮件通知"""
    try:
        smtp_server = config.get("smtp_server")
        smtp_port = config.get("smtp_port", 587)
        username = config.get("username")
        password = config.get("password")
        to_email = config.get("to_email")

        if not all([smtp_server, username, password, to_email]):
            print("邮件配置不完整")
            return False

        msg = MIMEMultipart()
        msg['From'] = username
        msg['To'] = to_email
        msg['Subject'] = title

        msg.attach(MIMEText(content, 'plain', 'utf-8'))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(msg)

        print(f"邮件通知发送成功: {username} -> {to_email}")
        return True

    except Exception as e:
        print(f"发送邮件通知失败: {e}")
        return False

async def _send_pushplus_notification(config: Dict[str, Any], title: str, content: str) -> bool:
    """发送PushPlus通知"""
    try:
        token = config.get("token")
        if not token:
            print("PushPlus token未配置")
            return False

        url = "http://www.pushplus.plus/send"
        template = config.get("template", "txt")

        data = {
            "token": token,
            "title": title,
            "content": content,
            "template": template
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, timeout=10) as response:
                result = await response.json()
                if result.get("code") == 200:
                    print(f"PushPlus通知发送成功")
                    return True
                else:
                    print(f"PushPlus发送失败: {result}")
                    return False

    except Exception as e:
        print(f"发送PushPlus通知失败: {e}")
        return False

async def _send_wxpusher_notification(config: Dict[str, Any], title: str, content: str) -> bool:
    """发送WxPusher通知"""
    try:
        app_token = config.get("app_token")
        uids = config.get("uids", [])

        if not app_token:
            print("WxPusher app_token未配置")
            return False

        if not uids or not isinstance(uids, list) or len(uids) == 0:
            print("WxPusher uids未配置")
            return False

        url = "http://wxpusher.zjiecode.com/api/send/message"
        content_type = config.get("content_type", 1)

        data = {
            "appToken": app_token,
            "content": content,
            "summary": title,
            "contentType": content_type,
            "uids": uids
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, timeout=10) as response:
                result = await response.json()
                if result.get("success"):
                    print(f"WxPusher通知发送成功")
                    return True
                else:
                    print(f"WxPusher发送失败: {result}")
                    return False

    except Exception as e:
        print(f"发送WxPusher通知失败: {e}")
        return False


# SendNotify配置相关API
@router.get("/sendnotify-config")
async def get_sendnotify_config(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """获取SendNotify配置"""
    try:
        config = db.query(SystemConfig).filter(
            SystemConfig.config_key == "sendnotify_notification_type"
        ).first()

        notification_type = config.config_value if config else None

        return {
            "notification_type": notification_type
        }
    except Exception as e:
        print(f"获取SendNotify配置失败: {e}")
        return {"notification_type": None}


@router.post("/sendnotify-config")
async def set_sendnotify_config(
    config_data: SendNotifyConfigRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """设置SendNotify配置"""
    try:
        # 如果设置了通知类型，验证该通知配置是否存在且已激活
        if config_data.notification_type:
            notification_config = db.query(NotificationConfig).filter(
                NotificationConfig.name == config_data.notification_type,
                NotificationConfig.is_active == True
            ).first()

            if not notification_config:
                raise HTTPException(
                    status_code=400,
                    detail=f"通知配置 {config_data.notification_type} 不存在或未激活"
                )

        # 查找现有配置
        config = db.query(SystemConfig).filter(
            SystemConfig.config_key == "sendnotify_notification_type"
        ).first()

        if config:
            # 更新现有配置
            config.config_value = config_data.notification_type or ""
            config.description = "SendNotify模块使用的默认通知方式"
        else:
            # 创建新配置
            config = SystemConfig(
                config_key="sendnotify_notification_type",
                config_value=config_data.notification_type or "",
                description="SendNotify模块使用的默认通知方式"
            )
            db.add(config)

        db.commit()
        db.refresh(config)

        return {
            "message": "SendNotify配置保存成功",
            "notification_type": config.config_value
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"设置SendNotify配置失败: {e}")
        raise HTTPException(status_code=500, detail="设置SendNotify配置失败")


async def _send_test_telegram(config: Dict[str, Any]) -> bool:
    """发送测试Telegram通知"""
    try:
        bot_token = config.get("bot_token")
        chat_id = config.get("chat_id")

        if not bot_token or not chat_id:
            print("Telegram配置不完整")
            return False

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

        # 构建测试消息
        title = "Pinchy系统 - Telegram通知测试"
        content = f"""
🤖 Pinchy系统Telegram通知测试

✅ 如果您收到这条消息，说明Telegram通知配置成功！

📋 配置信息：
• Bot Token: {bot_token[:8]}...{bot_token[-8:] if len(bot_token) > 16 else bot_token}
• Chat ID: {chat_id}

⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎉 您现在可以正常接收任务执行通知了！
        """.strip()

        # 获取用户配置的解析模式，默认为空（纯文本）
        parse_mode = config.get("parse_mode", "")

        data = {
            "chat_id": chat_id,
            "text": f"{title}\n\n{content}"
        }

        if parse_mode:
            data["parse_mode"] = parse_mode

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, timeout=10) as response:
                result = await response.json()
                if result.get("ok"):
                    print(f"测试Telegram通知发送成功: {result}")
                    return True
                else:
                    print(f"Telegram发送失败: {result}")
                    return False

    except Exception as e:
        print(f"发送测试Telegram通知失败: {e}")
        return False


async def _send_test_wecom(config: Dict[str, Any]) -> bool:
    """发送测试企业微信WebHook通知"""
    try:
        webhook_url = config.get("webhook_url")

        if not webhook_url:
            print("企业微信webhook_url未配置")
            return False

        # 构建测试消息
        title = "Pinchy系统 - 企业微信通知测试"
        content = f"""
📱 Pinchy系统企业微信通知测试

✅ 如果您收到这条消息，说明企业微信通知配置成功！

📋 配置信息：
• Webhook URL: {webhook_url[:30]}...

⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎉 您现在可以正常接收任务执行通知了！
        """.strip()

        # 获取用户配置的消息类型，默认为text
        msg_type = config.get("msg_type", "text")

        if msg_type == "text":
            data = {
                "msgtype": "text",
                "text": {
                    "content": f"{title}\n\n{content}"
                }
            }
        elif msg_type == "markdown":
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"## {title}\n\n{content}"
                }
            }
        else:
            # 默认使用text类型
            data = {
                "msgtype": "text",
                "text": {
                    "content": f"{title}\n\n{content}"
                }
            }

        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=data, timeout=10) as response:
                result = await response.json()
                if result.get("errcode") == 0:
                    print(f"测试企业微信通知发送成功: {result}")
                    return True
                else:
                    print(f"企业微信发送失败: {result}")
                    return False

    except Exception as e:
        print(f"发送测试企业微信通知失败: {e}")
        return False


async def _send_test_serverchan(config: Dict[str, Any]) -> bool:
    """发送测试Server酱通知"""
    try:
        send_key = config.get("send_key")

        if not send_key:
            print("Server酱send_key未配置")
            return False

        url = f"https://sctapi.ftqq.com/{send_key}.send"

        # 构建测试消息
        title = "Pinchy系统 - Server酱通知测试"
        content = f"""
📱 Pinchy系统Server酱通知测试

✅ 如果您收到这条消息，说明Server酱通知配置成功！

📋 配置信息：
• Send Key: {send_key[:8]}...{send_key[-8:] if len(send_key) > 16 else send_key}

⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎉 您现在可以正常接收任务执行通知了！
        """.strip()

        data = {
            "title": title,
            "desp": content
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, timeout=10) as response:
                result = await response.json()
                if result.get("code") == 0:
                    print(f"测试Server酱通知发送成功: {result}")
                    return True
                else:
                    print(f"Server酱发送失败: {result}")
                    return False

    except Exception as e:
        print(f"发送测试Server酱通知失败: {e}")
        return False


async def _send_test_dingtalk(config: Dict[str, Any]) -> bool:
    """发送测试钉钉通知"""
    try:
        webhook_url = config.get("webhook_url")
        secret = config.get("secret")

        if not webhook_url:
            print("钉钉webhook_url未配置")
            return False

        # 如果配置了签名密钥，需要计算签名
        if secret:
            import time
            import hmac
            import hashlib
            import base64
            import urllib.parse

            timestamp = str(round(time.time() * 1000))
            secret_enc = secret.encode('utf-8')
            string_to_sign = '{}\n{}'.format(timestamp, secret)
            string_to_sign_enc = string_to_sign.encode('utf-8')
            hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
            sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))

            webhook_url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

        # 构建测试消息
        title = "Pinchy系统 - 钉钉通知测试"
        content = f"""
📱 Pinchy系统钉钉通知测试

✅ 如果您收到这条消息，说明钉钉通知配置成功！

📋 配置信息：
• Webhook URL: {webhook_url[:30]}...
• 签名验证: {'已启用' if secret else '未启用'}

⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎉 您现在可以正常接收任务执行通知了！
        """.strip()

        # 获取用户配置的消息类型，默认为text
        msg_type = config.get("msg_type", "text")

        if msg_type == "text":
            data = {
                "msgtype": "text",
                "text": {
                    "content": f"{title}\n\n{content}"
                }
            }
        elif msg_type == "markdown":
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": f"## {title}\n\n{content}"
                }
            }
        else:
            # 默认使用text类型
            data = {
                "msgtype": "text",
                "text": {
                    "content": f"{title}\n\n{content}"
                }
            }

        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=data, timeout=10) as response:
                result = await response.json()
                if result.get("errcode") == 0:
                    print(f"测试钉钉通知发送成功: {result}")
                    return True
                else:
                    print(f"钉钉发送失败: {result}")
                    return False

    except Exception as e:
        print(f"发送测试钉钉通知失败: {e}")
        return False


async def _send_test_bark(config: Dict[str, Any]) -> bool:
    """发送测试Bark通知"""
    try:
        device_key = config.get("device_key")
        server_url = config.get("server_url", "https://api.day.app")

        if not device_key:
            print("Bark device_key未配置")
            return False

        # 构建URL
        url = f"{server_url.rstrip('/')}/{device_key}"

        # 构建测试消息
        title = "Pinchy系统 - Bark通知测试"
        content = f"""
📱 Pinchy系统Bark通知测试

✅ 如果您收到这条消息，说明Bark通知配置成功！

📋 配置信息：
• Device Key: {device_key[:8]}...{device_key[-8:] if len(device_key) > 16 else device_key}
• Server URL: {server_url}

⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎉 您现在可以正常接收任务执行通知了！
        """.strip()

        # 获取用户配置的参数
        sound = config.get("sound", "")
        group = config.get("group", "")

        data = {
            "title": title,
            "body": content
        }

        if sound:
            data["sound"] = sound
        if group:
            data["group"] = group

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, timeout=10) as response:
                result = await response.json()
                if result.get("code") == 200:
                    print(f"测试Bark通知发送成功: {result}")
                    return True
                else:
                    print(f"Bark发送失败: {result}")
                    return False

    except Exception as e:
        print(f"发送测试Bark通知失败: {e}")
        return False


async def _send_test_wecom_app(config: Dict[str, Any]) -> bool:
    """发送测试企业微信应用通知"""
    try:
        corp_id = config.get("corp_id")
        corp_secret = config.get("corp_secret")
        agent_id = config.get("agent_id")
        to_user = config.get("to_user", "@all")

        if not corp_id or not corp_secret or not agent_id:
            print("企业微信应用配置不完整")
            return False

        # 第一步：获取access_token
        token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corp_id}&corpsecret={corp_secret}"

        async with aiohttp.ClientSession() as session:
            async with session.get(token_url, timeout=10) as response:
                token_result = await response.json()
                if token_result.get("errcode") != 0:
                    print(f"获取企业微信access_token失败: {token_result}")
                    return False

                access_token = token_result.get("access_token")
                if not access_token:
                    print("企业微信access_token为空")
                    return False

            # 第二步：发送消息
            send_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"

            # 构建测试消息
            title = "Pinchy系统 - 企业微信应用通知测试"
            content = f"""📱 Pinchy系统企业微信应用通知测试

✅ 如果您收到这条消息，说明企业微信应用通知配置成功！

📋 配置信息：
• 企业ID: {corp_id}
• 应用ID: {agent_id}
• 接收用户: {to_user}

⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎉 您现在可以正常接收任务执行通知了！"""

            # 获取用户配置的消息类型，默认为text
            msg_type = config.get("msg_type", "text")

            if msg_type == "text":
                message_data = {
                    "touser": to_user,
                    "msgtype": "text",
                    "agentid": agent_id,
                    "text": {
                        "content": f"{title}\n\n{content}"
                    }
                }
            elif msg_type == "markdown":
                message_data = {
                    "touser": to_user,
                    "msgtype": "markdown",
                    "agentid": agent_id,
                    "markdown": {
                        "content": f"## {title}\n\n{content}"
                    }
                }
            else:
                # 默认使用text类型
                message_data = {
                    "touser": to_user,
                    "msgtype": "text",
                    "agentid": agent_id,
                    "text": {
                        "content": f"{title}\n\n{content}"
                    }
                }

            async with session.post(send_url, json=message_data, timeout=10) as response:
                result = await response.json()
                if result.get("errcode") == 0:
                    print(f"测试企业微信应用通知发送成功: {result}")
                    return True
                else:
                    print(f"企业微信应用发送失败: {result}")
                    return False

    except Exception as e:
        print(f"发送测试企业微信应用通知失败: {e}")
        return False


async def _send_wecom_notification(config: Dict[str, Any], title: str, content: str) -> bool:
    """发送企业微信WebHook通知"""
    try:
        webhook_url = config.get("webhook_url")

        if not webhook_url:
            print("企业微信webhook_url未配置")
            return False

        # 获取用户配置的消息类型，默认为text
        msg_type = config.get("msg_type", "text")

        if msg_type == "text":
            data = {
                "msgtype": "text",
                "text": {
                    "content": f"{title}\n\n{content}"
                }
            }
        elif msg_type == "markdown":
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"## {title}\n\n{content}"
                }
            }
        else:
            # 默认使用text类型
            data = {
                "msgtype": "text",
                "text": {
                    "content": f"{title}\n\n{content}"
                }
            }

        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=data, timeout=10) as response:
                result = await response.json()
                if result.get("errcode") == 0:
                    print(f"企业微信WebHook通知发送成功")
                    return True
                else:
                    print(f"企业微信WebHook发送失败: {result}")
                    return False

    except Exception as e:
        print(f"发送企业微信WebHook通知失败: {e}")
        return False


async def _send_wecom_app_notification(config: Dict[str, Any], title: str, content: str) -> bool:
    """发送企业微信应用通知"""
    try:
        corp_id = config.get("corp_id")
        corp_secret = config.get("corp_secret")
        agent_id = config.get("agent_id")
        to_user = config.get("to_user", "@all")

        if not corp_id or not corp_secret or not agent_id:
            print("企业微信应用配置不完整")
            return False

        # 第一步：获取access_token
        token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={corp_id}&corpsecret={corp_secret}"

        async with aiohttp.ClientSession() as session:
            async with session.get(token_url, timeout=10) as response:
                token_result = await response.json()
                if token_result.get("errcode") != 0:
                    print(f"获取企业微信access_token失败: {token_result}")
                    return False

                access_token = token_result.get("access_token")
                if not access_token:
                    print("企业微信access_token为空")
                    return False

            # 第二步：发送消息
            send_url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"

            # 获取用户配置的消息类型，默认为text
            msg_type = config.get("msg_type", "text")

            if msg_type == "text":
                message_data = {
                    "touser": to_user,
                    "msgtype": "text",
                    "agentid": agent_id,
                    "text": {
                        "content": f"{title}\n\n{content}"
                    }
                }
            elif msg_type == "markdown":
                message_data = {
                    "touser": to_user,
                    "msgtype": "markdown",
                    "agentid": agent_id,
                    "markdown": {
                        "content": f"## {title}\n\n{content}"
                    }
                }
            else:
                # 默认使用text类型
                message_data = {
                    "touser": to_user,
                    "msgtype": "text",
                    "agentid": agent_id,
                    "text": {
                        "content": f"{title}\n\n{content}"
                    }
                }

            async with session.post(send_url, json=message_data, timeout=10) as response:
                result = await response.json()
                if result.get("errcode") == 0:
                    print(f"企业微信应用通知发送成功")
                    return True
                else:
                    print(f"企业微信应用发送失败: {result}")
                    return False

    except Exception as e:
        print(f"发送企业微信应用通知失败: {e}")
        return False
