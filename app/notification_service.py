"""
通知服务模块
处理各种类型的通知发送
"""
import asyncio
import aiohttp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import NotificationConfig, TaskNotificationConfig, TaskLog
from app.database import SessionLocal


class NotificationService:
    """通知服务类"""
    
    def __init__(self):
        self.session = None
    
    async def send_task_notification(self, task_id: int, task_log: TaskLog):
        """发送任务通知"""
        db = SessionLocal()
        try:
            # 获取任务通知配置
            task_config = db.query(TaskNotificationConfig).filter(
                TaskNotificationConfig.task_id == task_id
            ).first()
            
            if not task_config or not task_config.notification_type:
                print(f"任务 {task_id} 没有配置通知")
                return
            
            # 检查是否只推送错误
            if task_config.error_only and task_log.status == "success":
                print(f"任务 {task_id} 配置为仅推送错误，跳过成功通知")
                return
            
            # 检查关键词过滤
            if task_config.keywords:
                keywords = [kw.strip() for kw in task_config.keywords.split(',') if kw.strip()]
                if keywords:
                    # 检查输出中是否包含关键词
                    output_text = (task_log.output or '') + (task_log.error_output or '')
                    if not any(keyword in output_text for keyword in keywords):
                        print(f"任务 {task_id} 输出不包含关键词，跳过通知")
                        return
            
            # 获取通知配置
            notification_config = db.query(NotificationConfig).filter(
                NotificationConfig.name == task_config.notification_type,
                NotificationConfig.is_active == True
            ).first()
            
            if not notification_config:
                print(f"通知配置 {task_config.notification_type} 不存在或未激活")
                return
            
            # 构建通知内容
            message = self._build_notification_message(task_log)
            
            # 根据通知类型发送
            success = False
            if notification_config.name == "email":
                success = await self._send_email_notification(notification_config.config, message)
            elif notification_config.name == "pushplus":
                success = await self._send_pushplus_notification(notification_config.config, message)
            elif notification_config.name == "wxpusher":
                success = await self._send_wxpusher_notification(notification_config.config, message)
            elif notification_config.name == "telegram":
                success = await self._send_telegram_notification(notification_config.config, message)
            elif notification_config.name == "wecom":
                success = await self._send_wecom_notification(notification_config.config, message)
            elif notification_config.name == "serverchan":
                success = await self._send_serverchan_notification(notification_config.config, message)
            elif notification_config.name == "dingtalk":
                success = await self._send_dingtalk_notification(notification_config.config, message)
            elif notification_config.name == "bark":
                success = await self._send_bark_notification(notification_config.config, message)
            
            if success:
                print(f"任务 {task_id} 通知发送成功")
            else:
                print(f"任务 {task_id} 通知发送失败")
                
        except Exception as e:
            print(f"发送任务通知时出错: {e}")
        finally:
            db.close()

    async def send_notification(self, notification_config: NotificationConfig, title: str, content: str) -> bool:
        """发送通用通知"""
        try:
            message = {
                "title": title,
                "content": content
            }

            # 根据通知类型发送
            success = False
            if notification_config.name == "email":
                success = await self._send_email_notification(notification_config.config, message)
            elif notification_config.name == "pushplus":
                success = await self._send_pushplus_notification(notification_config.config, message)
            elif notification_config.name == "wxpusher":
                success = await self._send_wxpusher_notification(notification_config.config, message)
            elif notification_config.name == "telegram":
                success = await self._send_telegram_notification(notification_config.config, message)
            elif notification_config.name == "wecom":
                success = await self._send_wecom_notification(notification_config.config, message)
            elif notification_config.name == "serverchan":
                success = await self._send_serverchan_notification(notification_config.config, message)
            elif notification_config.name == "dingtalk":
                success = await self._send_dingtalk_notification(notification_config.config, message)
            elif notification_config.name == "bark":
                success = await self._send_bark_notification(notification_config.config, message)

            return success

        except Exception as e:
            print(f"发送通知时出错: {e}")
            return False

    def _build_notification_message(self, task_log: TaskLog) -> Dict[str, str]:
        """构建通知消息"""
        status_text = {
            "success": "✅ 执行成功",
            "failed": "❌ 执行失败", 
            "stopped": "⏹️ 已停止"
        }.get(task_log.status, f"状态: {task_log.status}")
        
        # 计算执行时长
        duration = ""
        if task_log.start_time and task_log.end_time:
            delta = task_log.end_time - task_log.start_time
            total_seconds = int(delta.total_seconds())
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            if minutes > 0:
                duration = f"{minutes}分{seconds}秒"
            else:
                duration = f"{seconds}秒"
        
        # 构建消息
        title = f"Pinchy任务通知 - {task_log.task_name}"
        
        content_lines = [
            f"📋 任务名称: {task_log.task_name}",
            f"📊 执行状态: {status_text}",
        ]
        
        if task_log.start_time:
            content_lines.append(f"⏰ 开始时间: {task_log.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if task_log.end_time:
            content_lines.append(f"⏱️ 结束时间: {task_log.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if duration:
            content_lines.append(f"⌛ 执行时长: {duration}")
        
        if task_log.exit_code is not None:
            content_lines.append(f"🔢 退出代码: {task_log.exit_code}")
        
        # 添加输出内容（限制长度）
        if task_log.output:
            output_preview = task_log.output[:500] + "..." if len(task_log.output) > 500 else task_log.output
            content_lines.append(f"\n📤 标准输出:\n{output_preview}")
        
        if task_log.error_output:
            error_preview = task_log.error_output[:500] + "..." if len(task_log.error_output) > 500 else task_log.error_output
            content_lines.append(f"\n❗ 错误输出:\n{error_preview}")
        
        content = "\n".join(content_lines)
        
        return {
            "title": title,
            "content": content
        }
    
    async def _send_email_notification(self, config: Dict[str, Any], message: Dict[str, str]) -> bool:
        """发送邮件通知"""
        try:
            # 邮件配置
            smtp_server = config.get("smtp_server")
            smtp_port = config.get("smtp_port", 587)
            username = config.get("username")
            password = config.get("password")
            to_email = config.get("to_email")
            
            if not all([smtp_server, username, password, to_email]):
                print("邮件配置不完整")
                return False
            
            # 创建邮件
            msg = MIMEMultipart()
            msg['From'] = username
            msg['To'] = to_email
            msg['Subject'] = message["title"]
            
            # 添加邮件内容
            msg.attach(MIMEText(message["content"], 'plain', 'utf-8'))
            
            # 发送邮件
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            print(f"发送邮件失败: {e}")
            return False
    
    async def _send_pushplus_notification(self, config: Dict[str, Any], message: Dict[str, str]) -> bool:
        """发送PushPlus通知"""
        try:
            token = config.get("token")
            if not token:
                print("PushPlus token未配置")
                return False
            
            url = "http://www.pushplus.plus/send"
            # 获取用户配置的模板类型，默认为txt
            template = config.get("template", "txt")

            data = {
                "token": token,
                "title": message["title"],
                "content": message["content"],
                "template": template
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    result = await response.json()
                    if result.get("code") == 200:
                        return True
                    else:
                        print(f"PushPlus发送失败: {result}")
                        return False
                        
        except Exception as e:
            print(f"发送PushPlus通知失败: {e}")
            return False
    
    async def _send_wxpusher_notification(self, config: Dict[str, Any], message: Dict[str, str]) -> bool:
        """发送WxPusher通知"""
        try:
            app_token = config.get("app_token")
            uids = config.get("uids", [])
            
            if not app_token or not uids:
                print("WxPusher配置不完整")
                return False
            
            url = "http://wxpusher.zjiecode.com/api/send/message"
            # 获取用户配置的内容类型，默认为1（文本类型）
            content_type = config.get("content_type", 1)

            data = {
                "appToken": app_token,
                "content": message["content"],
                "summary": message["title"],
                "contentType": content_type,
                "uids": uids
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    result = await response.json()
                    if result.get("success"):
                        return True
                    else:
                        print(f"WxPusher发送失败: {result}")
                        return False
                        
        except Exception as e:
            print(f"发送WxPusher通知失败: {e}")
            return False

    async def _send_telegram_notification(self, config: Dict[str, Any], message: Dict[str, str]) -> bool:
        """发送Telegram机器人通知"""
        try:
            bot_token = config.get("bot_token")
            chat_id = config.get("chat_id")

            if not bot_token or not chat_id:
                print("Telegram配置不完整")
                return False

            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

            # 获取用户配置的解析模式，默认为空（纯文本）
            parse_mode = config.get("parse_mode", "")

            data = {
                "chat_id": chat_id,
                "text": f"{message['title']}\n\n{message['content']}"
            }

            if parse_mode:
                data["parse_mode"] = parse_mode

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    result = await response.json()
                    if result.get("ok"):
                        return True
                    else:
                        print(f"Telegram发送失败: {result}")
                        return False

        except Exception as e:
            print(f"发送Telegram通知失败: {e}")
            return False

    async def _send_wecom_notification(self, config: Dict[str, Any], message: Dict[str, str]) -> bool:
        """发送企业微信机器人通知"""
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
                        "content": f"{message['title']}\n\n{message['content']}"
                    }
                }
            elif msg_type == "markdown":
                data = {
                    "msgtype": "markdown",
                    "markdown": {
                        "content": f"## {message['title']}\n\n{message['content']}"
                    }
                }
            else:
                # 默认使用text类型
                data = {
                    "msgtype": "text",
                    "text": {
                        "content": f"{message['title']}\n\n{message['content']}"
                    }
                }

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=data) as response:
                    result = await response.json()
                    if result.get("errcode") == 0:
                        return True
                    else:
                        print(f"企业微信发送失败: {result}")
                        return False

        except Exception as e:
            print(f"发送企业微信通知失败: {e}")
            return False

    async def _send_serverchan_notification(self, config: Dict[str, Any], message: Dict[str, str]) -> bool:
        """发送Server酱通知"""
        try:
            send_key = config.get("send_key")

            if not send_key:
                print("Server酱send_key未配置")
                return False

            url = f"https://sctapi.ftqq.com/{send_key}.send"

            data = {
                "title": message["title"],
                "desp": message["content"]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as response:
                    result = await response.json()
                    if result.get("code") == 0:
                        return True
                    else:
                        print(f"Server酱发送失败: {result}")
                        return False

        except Exception as e:
            print(f"发送Server酱通知失败: {e}")
            return False

    async def _send_dingtalk_notification(self, config: Dict[str, Any], message: Dict[str, str]) -> bool:
        """发送钉钉机器人通知"""
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

            # 获取用户配置的消息类型，默认为text
            msg_type = config.get("msg_type", "text")

            if msg_type == "text":
                data = {
                    "msgtype": "text",
                    "text": {
                        "content": f"{message['title']}\n\n{message['content']}"
                    }
                }
            elif msg_type == "markdown":
                data = {
                    "msgtype": "markdown",
                    "markdown": {
                        "title": message["title"],
                        "text": f"## {message['title']}\n\n{message['content']}"
                    }
                }
            else:
                # 默认使用text类型
                data = {
                    "msgtype": "text",
                    "text": {
                        "content": f"{message['title']}\n\n{message['content']}"
                    }
                }

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=data) as response:
                    result = await response.json()
                    if result.get("errcode") == 0:
                        return True
                    else:
                        print(f"钉钉发送失败: {result}")
                        return False

        except Exception as e:
            print(f"发送钉钉通知失败: {e}")
            return False

    async def _send_bark_notification(self, config: Dict[str, Any], message: Dict[str, str]) -> bool:
        """发送Bark通知"""
        try:
            device_key = config.get("device_key")
            server_url = config.get("server_url", "https://api.day.app")

            if not device_key:
                print("Bark device_key未配置")
                return False

            # 构建URL
            url = f"{server_url.rstrip('/')}/{device_key}"

            # 获取用户配置的参数
            sound = config.get("sound", "")
            group = config.get("group", "")

            data = {
                "title": message["title"],
                "body": message["content"]
            }

            if sound:
                data["sound"] = sound
            if group:
                data["group"] = group

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    result = await response.json()
                    if result.get("code") == 200:
                        return True
                    else:
                        print(f"Bark发送失败: {result}")
                        return False

        except Exception as e:
            print(f"发送Bark通知失败: {e}")
            return False


# 全局通知服务实例
notification_service = NotificationService()
