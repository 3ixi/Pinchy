"""
接口调试相关的API路由
"""
import json
import time
import re
import requests
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import ApiDebugConfig, ApiDebugLog, EnvironmentVariable, NotificationConfig
from app.auth import get_current_user, User
from app.scheduler import task_scheduler
# 延迟导入避免循环导入
# from app.routers.notifications import send_notification

router = APIRouter(prefix="/api/debug", tags=["api_debug"])

# Pydantic模型
class ApiDebugConfigCreate(BaseModel):
    name: str
    description: Optional[str] = None
    method: str = "GET"
    url: str
    headers: dict = {}
    payload: Optional[str] = None
    notification_type: Optional[str] = None
    notification_enabled: bool = False
    notification_condition: str = "always"
    cron_expression: Optional[str] = None
    is_active: bool = False

class ApiDebugConfigUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    method: Optional[str] = None
    url: Optional[str] = None
    headers: Optional[dict] = None
    payload: Optional[str] = None
    notification_type: Optional[str] = None
    notification_enabled: Optional[bool] = None
    notification_condition: Optional[str] = None
    cron_expression: Optional[str] = None
    is_active: Optional[bool] = None

class ApiDebugExecuteRequest(BaseModel):
    method: str = "GET"
    url: str
    headers: dict = {}
    payload: Optional[str] = None
    notification_type: Optional[str] = None
    notification_enabled: bool = False
    notification_condition: str = "always"

class ImportRequest(BaseModel):
    content: str

# 变量替换函数
def replace_variables(text: str, env_vars: dict) -> str:
    """替换文本中的变量"""
    if not text:
        return text

    # 生成统一的时间戳
    timestamp_10 = str(int(time.time()))
    timestamp_13 = str(int(time.time() * 1000))

    # 替换时间戳变量
    text = re.sub(r'\[timestmp\.10\]', timestamp_10, text)
    text = re.sub(r'\[timestmp\.13\]', timestamp_13, text)
    text = re.sub(r'\[timestmp\]', timestamp_13, text)  # 默认13位

    # 替换随机数变量
    def replace_random_var(match):
        range_str = match.group(1)
        try:
            # 解析范围，支持格式：100-500
            if '-' in range_str:
                min_val, max_val = range_str.split('-', 1)
                min_val = int(min_val.strip())
                max_val = int(max_val.strip())
                if min_val <= max_val:
                    import random
                    return str(random.randint(min_val, max_val))
            # 如果格式不正确，保持原样
            return f'[random.{range_str}]'
        except (ValueError, TypeError):
            # 如果解析失败，保持原样
            return f'[random.{range_str}]'

    text = re.sub(r'\[random\.([^]]+)\]', replace_random_var, text)

    # 替换环境变量
    def replace_env_var(match):
        var_name = match.group(1)
        return env_vars.get(var_name, f'[getenv.{var_name}]')  # 如果找不到变量，保持原样

    text = re.sub(r'\[getenv\.([^]]+)\]', replace_env_var, text)

    return text

# 解析cURL命令
def parse_curl(curl_command: str) -> dict:
    """解析cURL命令"""
    try:
        result = {
            "method": "GET",
            "url": "",
            "headers": {},
            "payload": ""
        }

        # 清理命令，移除Windows的^换行符和多余空格
        cleaned_command = re.sub(r'\s*\^\s*\n\s*', ' ', curl_command)
        cleaned_command = re.sub(r'\s+', ' ', cleaned_command).strip()

        # 提取URL - 支持各种格式
        url_patterns = [
            r'curl\s+\^?"([^"]+)"\^?',     # Windows格式: curl ^"url"^
            r'curl\s+\'([^\']+)\'',        # 单引号: curl 'url'
            r'curl\s+"([^"]+)"',           # 双引号: curl "url"
            r'curl\s+([^\s-]+)',           # 不带引号: curl url
        ]

        for pattern in url_patterns:
            url_match = re.search(pattern, cleaned_command)
            if url_match:
                result["url"] = url_match.group(1)
                break

        # 提取方法
        method_patterns = [
            r'-X\s+([A-Z]+)',
            r'--request\s+([A-Z]+)'
        ]

        for pattern in method_patterns:
            method_match = re.search(pattern, cleaned_command, re.IGNORECASE)
            if method_match:
                result["method"] = method_match.group(1).upper()
                break

        # 提取请求头 - 支持Windows格式和标准格式
        header_patterns = [
            r'-H\s+\^?"([^:]+):\s*([^"]*?)"\^?',     # Windows: -H ^"key: value"^
            r'-H\s+\'([^:]+):\s*([^\']*)\'',         # 单引号: -H 'key: value'
            r'-H\s+"([^:]+):\s*([^"]*)"',            # 双引号: -H "key: value"
            r'--header\s+\^?"([^:]+):\s*([^"]*?)"\^?', # Windows: --header ^"key: value"^
            r'--header\s+\'([^:]+):\s*([^\']*)\'',   # 单引号: --header 'key: value'
            r'--header\s+"([^:]+):\s*([^"]*)"',      # 双引号: --header "key: value"
        ]

        for pattern in header_patterns:
            header_matches = re.findall(pattern, cleaned_command)
            for header_name, header_value in header_matches:
                result["headers"][header_name.strip()] = header_value.strip()

        # 提取Cookie
        cookie_patterns = [
            r'-b\s+\^?"([^"]*?)"\^?',        # Windows: -b ^"cookies"^
            r'-b\s+\'([^\']*)\'',            # 单引号: -b 'cookies'
            r'-b\s+"([^"]*)"',               # 双引号: -b "cookies"
            r'--cookie\s+\^?"([^"]*?)"\^?',  # Windows: --cookie ^"cookies"^
            r'--cookie\s+\'([^\']*)\'',      # 单引号: --cookie 'cookies'
            r'--cookie\s+"([^"]*)"',         # 双引号: --cookie "cookies"
        ]

        for pattern in cookie_patterns:
            cookie_match = re.search(pattern, cleaned_command)
            if cookie_match:
                result["headers"]["Cookie"] = cookie_match.group(1)
                break

        # 提取数据/请求体
        data_patterns = [
            r'--data\s+[\'"]([^\'"]*)[\'"]',
            r'--data-raw\s+[\'"]([^\'"]*)[\'"]',
            r'-d\s+[\'"]([^\'"]*)[\'"]',
        ]

        for pattern in data_patterns:
            data_match = re.search(pattern, cleaned_command)
            if data_match:
                result["payload"] = data_match.group(1)
                if result["method"] == "GET":
                    result["method"] = "POST"  # 有数据时默认为POST
                break

        # 清理所有数据中的Windows特殊字符^
        def clean_windows_chars(text):
            if isinstance(text, str):
                return text.replace('^', '')
            return text

        # 清理URL
        result["url"] = clean_windows_chars(result["url"])

        # 清理payload
        result["payload"] = clean_windows_chars(result["payload"])

        # 清理headers
        cleaned_headers = {}
        for key, value in result["headers"].items():
            cleaned_key = clean_windows_chars(key)
            cleaned_value = clean_windows_chars(value)
            cleaned_headers[cleaned_key] = cleaned_value
        result["headers"] = cleaned_headers

        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"cURL解析失败: {str(e)}")

# 解析fetch命令
def parse_fetch(fetch_command: str) -> dict:
    """解析fetch命令"""
    try:
        result = {
            "method": "GET",
            "url": "",
            "headers": {},
            "payload": ""
        }

        # 清理命令，移除多余的空格和换行
        cleaned_command = re.sub(r'\s+', ' ', fetch_command).strip()

        # 提取URL
        url_match = re.search(r'fetch\s*\(\s*[\'"]([^\'"]+)[\'"]', cleaned_command)
        if url_match:
            result["url"] = url_match.group(1)

        # 提取方法
        method_match = re.search(r'[\'"]method[\'"]\s*:\s*[\'"]([A-Z]+)[\'"]', cleaned_command, re.IGNORECASE)
        if method_match:
            result["method"] = method_match.group(1).upper()

        # 提取请求头 - 更强大的解析
        headers_match = re.search(r'[\'"]headers[\'"]\s*:\s*\{([^}]+)\}', cleaned_command, re.DOTALL)
        if headers_match:
            headers_content = headers_match.group(1)

            # 解析各种格式的键值对
            header_patterns = [
                r'[\'"]([^\'":]+)[\'"]\s*:\s*[\'"]([^\'"]+)[\'"]',  # "key": "value"
                r'([a-zA-Z-]+)\s*:\s*[\'"]([^\'"]+)[\'"]',         # key: "value"
            ]

            for pattern in header_patterns:
                header_pairs = re.findall(pattern, headers_content)
                for header_name, header_value in header_pairs:
                    result["headers"][header_name] = header_value

        # 提取body - 支持多种格式
        body_patterns = [
            r'[\'"]body[\'"]\s*:\s*[\'"]([^\'"]*)[\'"]',  # "body": "content"
            r'[\'"]body[\'"]\s*:\s*null',                # "body": null
            r'[\'"]body[\'"]\s*:\s*([^,}]+)',           # "body": variable
        ]

        for pattern in body_patterns:
            body_match = re.search(pattern, cleaned_command)
            if body_match:
                body_content = body_match.group(1) if body_match.lastindex else ""
                if body_content and body_content != "null":
                    result["payload"] = body_content
                    if result["method"] == "GET":
                        result["method"] = "POST"  # 有body时默认为POST
                break

        # 提取referrer作为Referer头
        referrer_match = re.search(r'[\'"]referrer[\'"]\s*:\s*[\'"]([^\'"]+)[\'"]', cleaned_command)
        if referrer_match:
            result["headers"]["Referer"] = referrer_match.group(1)

        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"fetch解析失败: {str(e)}")

@router.get("/configs")
async def get_debug_configs(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """获取所有接口调试配置"""
    configs = db.query(ApiDebugConfig).all()
    result = []
    for config in configs:
        result.append({
            "id": config.id,
            "name": config.name,
            "description": config.description,
            "method": config.method,
            "url": config.url,
            "headers": config.headers,
            "payload": config.payload,
            "notification_type": config.notification_type,
            "notification_enabled": config.notification_enabled,
            "notification_condition": config.notification_condition,
            "cron_expression": config.cron_expression,
            "is_active": config.is_active,
            "created_at": config.created_at.isoformat(),
            "updated_at": config.updated_at.isoformat() if config.updated_at else None
        })
    return result

@router.post("/configs")
async def create_debug_config(
    config_data: ApiDebugConfigCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """创建接口调试配置"""
    config = ApiDebugConfig(**config_data.dict())
    db.add(config)
    db.commit()
    db.refresh(config)

    # 如果配置启用且有cron表达式，添加到调度器
    if config.is_active and config.cron_expression:
        task_scheduler.add_debug_config(config)

    return {"message": "配置创建成功", "id": config.id}

@router.put("/configs/{config_id}")
async def update_debug_config(
    config_id: int,
    config_data: ApiDebugConfigUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """更新接口调试配置"""
    config = db.query(ApiDebugConfig).filter(ApiDebugConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")

    # 先从调度器移除旧配置
    task_scheduler.remove_debug_config(config_id)

    for field, value in config_data.dict(exclude_unset=True).items():
        setattr(config, field, value)

    db.commit()

    # 如果配置启用且有cron表达式，重新添加到调度器
    if config.is_active and config.cron_expression:
        task_scheduler.add_debug_config(config)

    return {"message": "配置更新成功"}

@router.delete("/configs/{config_id}")
async def delete_debug_config(
    config_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """删除接口调试配置"""
    config = db.query(ApiDebugConfig).filter(ApiDebugConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")

    # 从调度器移除配置
    task_scheduler.remove_debug_config(config_id)

    db.delete(config)
    db.commit()
    return {"message": "配置删除成功"}

@router.post("/execute")
async def execute_debug_request(
    request_data: ApiDebugExecuteRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """执行接口调试请求"""
    start_time = datetime.now()
    
    # 获取环境变量
    env_vars = {}
    env_records = db.query(EnvironmentVariable).all()
    for env_record in env_records:
        env_vars[env_record.key] = env_record.value
    
    # 替换变量
    url = replace_variables(request_data.url, env_vars)

    # 先替换payload中的变量，因为Content-Length需要基于替换后的payload计算
    payload = replace_variables(request_data.payload, env_vars) if request_data.payload else None

    # 处理headers，特别注意Content-Length的处理
    headers = {}
    auto_calculate_content_length = False

    for key, value in request_data.headers.items():
        # 检查是否需要自动计算Content-Length
        if key.lower() == 'content-length' and value == '自动计算':
            auto_calculate_content_length = True
            continue
        headers[replace_variables(key, env_vars)] = replace_variables(value, env_vars)

    # 自动设置Host头
    try:
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        if parsed_url.netloc:
            headers['Host'] = parsed_url.netloc
    except:
        pass

    # 自动设置Content-Length（基于替换变量后的payload）
    if payload and request_data.method.upper() in ['POST', 'PUT', 'PATCH']:
        if auto_calculate_content_length or 'Content-Length' not in headers:
            headers['Content-Length'] = str(len(payload.encode('utf-8')))
    
    try:
        # 发送请求，确保正确处理UTF-8编码
        if payload:
            # 将payload编码为UTF-8字节
            payload_bytes = payload.encode('utf-8')
            response = requests.request(
                method=request_data.method.upper(),
                url=url,
                headers=headers,
                data=payload_bytes,
                timeout=30
            )
        else:
            response = requests.request(
                method=request_data.method.upper(),
                url=url,
                headers=headers,
                timeout=30
            )
        
        end_time = datetime.now()
        response_time = int((end_time - start_time).total_seconds() * 1000)
        
        result = {
            "status": "success",
            "response": {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.text,
                "response_time": response_time
            },
            "request": {
                "method": request_data.method.upper(),
                "url": url,
                "headers": headers,
                "payload": payload
            }
        }
        
        # 发送通知
        if request_data.notification_enabled and request_data.notification_type:
            should_notify = (
                request_data.notification_condition == "always" or
                (request_data.notification_condition == "success" and response.status_code < 400) or
                (request_data.notification_condition == "error" and response.status_code >= 400)
            )
            
            if should_notify:
                try:
                    notification_config = db.query(NotificationConfig).filter(
                        NotificationConfig.name == request_data.notification_type,
                        NotificationConfig.is_active == True
                    ).first()
                    
                    if notification_config:
                        message = f"接口调试结果\n"
                        message += f"URL: {url}\n"
                        message += f"方法: {request_data.method.upper()}\n"
                        message += f"状态码: {response.status_code}\n"
                        message += f"响应时间: {response_time}ms\n"
                        # 增加响应内容长度，最多显示1000字符
                        response_content = response.text[:1000]
                        if len(response.text) > 1000:
                            response_content += "...(内容过长已截断)"
                        message += f"响应内容: {response_content}"

                        # 延迟导入避免循环导入
                        from app.routers.notifications import send_notification
                        await send_notification(notification_config, "接口调试通知", message)
                except Exception as e:
                    print(f"发送通知失败: {str(e)}")
        
        return result
        
    except Exception as e:
        end_time = datetime.now()
        response_time = int((end_time - start_time).total_seconds() * 1000)
        
        result = {
            "status": "error",
            "error": str(e),
            "response_time": response_time,
            "request": {
                "method": request_data.method.upper(),
                "url": url,
                "headers": headers,
                "payload": payload
            }
        }
        
        # 发送错误通知
        if request_data.notification_enabled and request_data.notification_type and request_data.notification_condition in ["always", "error"]:
            try:
                notification_config = db.query(NotificationConfig).filter(
                    NotificationConfig.name == request_data.notification_type,
                    NotificationConfig.is_active == True
                ).first()
                
                if notification_config:
                    message = f"接口调试失败\n"
                    message += f"URL: {url}\n"
                    message += f"方法: {request_data.method.upper()}\n"
                    message += f"错误信息: {str(e)}\n"
                    message += f"响应时间: {response_time}ms"

                    # 延迟导入避免循环导入
                    from app.routers.notifications import send_notification
                    await send_notification(notification_config, "接口调试错误通知", message)
            except Exception as e:
                print(f"发送通知失败: {str(e)}")
        
        return result

@router.post("/import")
async def import_request(
    import_data: ImportRequest,
    _: User = Depends(get_current_user)
):
    """导入cURL或fetch请求"""
    content = import_data.content.strip()
    
    if content.startswith('curl'):
        return parse_curl(content)
    elif 'fetch(' in content:
        return parse_fetch(content)
    else:
        raise HTTPException(status_code=400, detail="无法识别的请求格式，请输入cURL或fetch命令")

@router.get("/variables")
async def get_variables(
    _: User = Depends(get_current_user)
):
    """获取可用变量列表"""
    variables = [
        {
            "name": "[timestmp.10]",
            "description": "当前秒级时间戳（10位）",
            "example": str(int(time.time()))
        },
        {
            "name": "[timestmp.13]",
            "description": "当前毫秒级时间戳（13位）",
            "example": str(int(time.time() * 1000))
        },
        {
            "name": "[getenv.XXX]",
            "description": "环境变量（XXX为变量名）",
            "example": "将XXX替换为具体的环境变量名"
        },
        {
            "name": "[random.最小值-最大值]",
            "description": "生成指定范围的随机数",
            "example": "[random.100-500] 生成100到500之间的随机数"
        }
    ]

    return variables
