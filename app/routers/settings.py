"""
系统设置相关路由
"""
import subprocess
import sys
import platform
import requests
import ssl
import uuid
import json
import os
import tarfile
import tempfile
import shutil
import sqlite3
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from app.database import get_db
from app.auth import get_current_user, get_password_hash, verify_password
from app.models import User, SystemVersion, SystemUUID, SystemConfig, TaskLog, NotificationConfig, EnvironmentVariable
from app.security import security_manager
from app.version import get_current_version, get_version_description, get_version_info, is_newer_version
from app.timezone_utils import get_available_timezones, get_timezone_offset, validate_timezone, get_system_timezone, set_system_timezone

router = APIRouter(prefix="/api/settings", tags=["系统设置"])

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class ChangeUsernameRequest(BaseModel):
    new_username: str
    password: str  # 需要当前密码确认

class ColorSchemeRequest(BaseModel):
    color_scheme: str

class SecurityConfigRequest(BaseModel):
    captcha_enabled: bool
    ip_blocking_enabled: bool
    mfa_enabled: bool
    mfa_notification_type: Optional[str] = None

class SecurityConfigResponse(BaseModel):
    captcha_enabled: bool
    ip_blocking_enabled: bool
    mfa_enabled: bool
    mfa_notification_type: Optional[str] = None
    available_notifications: list

class CommandConfigRequest(BaseModel):
    python_command: str
    nodejs_command: str
    python_package_manager: str
    nodejs_package_manager: str

class CommandConfigResponse(BaseModel):
    python_command: str
    nodejs_command: str
    python_package_manager: str
    nodejs_package_manager: str

class CommandTestRequest(BaseModel):
    command_type: str  # 'python' or 'nodejs'
    command: str

class CommandTestResponse(BaseModel):
    success: bool
    message: str
    version: Optional[str] = None

class PackageManagerTestRequest(BaseModel):
    manager_type: str  # 'python' or 'nodejs'
    manager: str

class PackageManagerTestResponse(BaseModel):
    success: bool
    message: str
    version: Optional[str] = None

class SystemInfo(BaseModel):
    python_version: str
    nodejs_version: Optional[str]
    system_info: dict
    timezone_info: dict

class LogCleanupSettings(BaseModel):
    enabled: bool
    retention_days: int

class VersionCheckResponse(BaseModel):
    current_version: str
    latest_version: Optional[str] = None
    has_update: bool = False
    upgrade_date: Optional[str] = None
    download_url: Optional[str] = None
    upgrade_info: Optional[str] = None
    created_at: Optional[str] = None  # 系统创建时间

class TimezoneInfo(BaseModel):
    name: str
    display_name: str
    offset: str

class TimezoneConfigRequest(BaseModel):
    timezone: str

class TimezoneConfigResponse(BaseModel):
    current_timezone: str
    current_timezone_display: str
    current_offset: str
    available_timezones: list[TimezoneInfo]

class BackupResponse(BaseModel):
    message: str
    filename: str
    size: int

class RestoreResponse(BaseModel):
    message: str
    files_restored: int
    tables_restored: int

@router.get("/system-info", response_model=SystemInfo)
async def get_system_info(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取系统信息"""
    try:
        # 获取Python版本
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        # 获取Node.js版本
        nodejs_version = None
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            nodejs_version = result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            nodejs_version = "未安装或未找到"

        # 获取系统信息
        import platform
        system_info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor()
        }

        # 获取时区信息
        from app.timezone_utils import get_current_time, format_datetime
        current_timezone = get_system_timezone(db)
        current_time = get_current_time(db)

        timezone_info = {
            "current_timezone": current_timezone,
            "current_time": format_datetime(current_time, db, "%Y-%m-%d %H:%M:%S"),
            "timezone_offset": get_timezone_offset(current_timezone),
            "utc_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        return SystemInfo(
            python_version=python_version,
            nodejs_version=nodejs_version,
            system_info=system_info,
            timezone_info=timezone_info
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统信息失败: {str(e)}")

@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """修改密码"""
    # 验证旧密码
    if not verify_password(password_data.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="旧密码错误")
    
    # 更新密码
    current_user.password_hash = get_password_hash(password_data.new_password)
    db.commit()
    
    return {"message": "密码修改成功"}

@router.post("/change-username")
async def change_username(
    username_data: ChangeUsernameRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """修改用户名"""
    # 验证当前密码
    if not verify_password(username_data.password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="密码错误")
    
    # 检查新用户名是否已存在
    existing_user = db.query(User).filter(
        User.username == username_data.new_username,
        User.id != current_user.id
    ).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 更新用户名
    current_user.username = username_data.new_username
    db.commit()
    
    return {"message": "用户名修改成功"}

@router.get("/user-info")
async def get_user_info(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "updated_at": current_user.updated_at.isoformat() if current_user.updated_at else None
    }

@router.get("/version")
async def get_system_version(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取系统版本"""
    version = db.query(SystemVersion).filter(SystemVersion.is_current == True).first()
    if not version:
        # 如果数据库中没有版本信息，返回应用配置的版本
        current_version = get_current_version()
        current_description = get_version_description()
        version_info = get_version_info(current_version)

        return {
            "version": current_version,
            "description": current_description,
            "release_date": version_info.get("release_date"),
            "features": version_info.get("features", []),
            "bug_fixes": version_info.get("bug_fixes", []),
            "source": "config"  # 标识来源于配置文件
        }

    # 从数据库获取版本信息，并补充详细信息
    version_info = get_version_info(version.version)
    return {
        "version": version.version,
        "description": version.description,
        "release_date": version_info.get("release_date"),
        "features": version_info.get("features", []),
        "bug_fixes": version_info.get("bug_fixes", []),
        "source": "database"  # 标识来源于数据库
    }

@router.get("/version-history")
async def get_version_history(current_user: User = Depends(get_current_user)):
    """获取版本历史记录"""
    from app.version import VERSION_HISTORY, compare_versions

    # 获取所有版本并按版本号倒序排列
    versions = []
    for version, info in VERSION_HISTORY.items():
        versions.append({
            "version": version,
            "release_date": info.get("release_date"),
            "description": info.get("description"),
            "features": info.get("features", []),
            "bug_fixes": info.get("bug_fixes", [])
        })

    # 按版本号倒序排列（最新版本在前）
    versions.sort(key=lambda x: x["version"], reverse=True)

    return {"versions": versions}

@router.get("/color-scheme")
async def get_color_scheme(current_user: User = Depends(get_current_user)):
    """获取用户配色方案"""
    return {"color_scheme": current_user.color_scheme}

@router.post("/color-scheme")
async def update_color_scheme(
    color_data: ColorSchemeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户配色方案"""
    # 验证配色方案是否有效
    valid_schemes = ["blue", "green", "purple", "gray", "orange", "dark"]
    if color_data.color_scheme not in valid_schemes:
        raise HTTPException(status_code=400, detail="无效的配色方案")

    # 更新配色方案
    current_user.color_scheme = color_data.color_scheme
    db.commit()

    return {"message": "配色方案更新成功", "color_scheme": color_data.color_scheme}

@router.get("/check-environment")
async def check_environment(current_user: User = Depends(get_current_user)):
    """检查Python和Node.js环境"""
    result = {
        "python": {"installed": False, "version": None},
        "nodejs": {"installed": False, "version": None}
    }

    # 检查Python环境
    try:
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        result["python"]["installed"] = True
        result["python"]["version"] = python_version
    except Exception:
        pass

    # 检查Node.js环境
    try:
        # 在Windows上需要使用shell=True
        import platform
        is_windows = platform.system().lower() == 'windows'

        nodejs_result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            shell=is_windows
        )
        if nodejs_result.returncode == 0:
            result["nodejs"]["installed"] = True
            result["nodejs"]["version"] = nodejs_result.stdout.strip()
    except Exception as e:
        print(f"检查Node.js环境失败: {str(e)}")
        pass

    return result

def get_or_create_system_uuid(db: Session) -> str:
    """获取或创建系统UUID"""
    system_uuid = db.query(SystemUUID).first()
    if not system_uuid:
        # 创建新的UUID
        new_uuid = str(uuid.uuid4())
        system_uuid = SystemUUID(uuid=new_uuid)
        db.add(system_uuid)
        db.commit()
        db.refresh(system_uuid)
        print(f"已生成新的系统UUID: {new_uuid}")
    return str(system_uuid.uuid)

def create_or_update_system_env_var(db: Session, key: str, value: str, description: Optional[str] = None):
    """创建或更新系统级环境变量"""
    try:
        # 查找是否已存在该环境变量
        env_var = db.query(EnvironmentVariable).filter(EnvironmentVariable.key == key).first()

        if env_var:
            # 更新现有变量
            env_var.value = value
            if description:
                env_var.description = description
            print(f"已更新系统环境变量: {key}")
        else:
            # 创建新的系统级环境变量
            env_var = EnvironmentVariable(
                key=key,
                value=value,
                description=description or f"系统自动创建的环境变量",
                is_system=True  # 标记为系统级变量
            )
            db.add(env_var)
            print(f"已创建系统环境变量: {key}")

        db.commit()
        db.refresh(env_var)
        return env_var
    except Exception as e:
        print(f"创建/更新系统环境变量失败: {str(e)}")
        db.rollback()
        return None

async def initialize_system_env_vars(db: Session):
    """初始化系统环境变量"""
    import asyncio
    import time

    max_retries = 60  # 最多等待60秒（60次重试，每次1秒）
    retry_count = 0

    while retry_count < max_retries:
        try:
            # 尝试获取系统UUID
            system_uuid = get_or_create_system_uuid(db)
            if system_uuid:
                # 创建或更新 pinchyX 环境变量
                create_or_update_system_env_var(
                    db=db,
                    key="pinchyX",
                    value=system_uuid,
                    description="系统UUID标识符，用于脚本判断运行环境"
                )
                print(f"✅ 系统环境变量 pinchyX 已设置: {system_uuid}")

                # 初始化命令配置
                initialize_command_config_from_env(db)

                return True
            else:
                print(f"⚠️ 系统UUID获取失败，等待重试... ({retry_count + 1}/{max_retries})")
        except Exception as e:
            print(f"⚠️ 初始化系统环境变量失败: {str(e)}，等待重试... ({retry_count + 1}/{max_retries})")

        retry_count += 1
        if retry_count < max_retries:
            await asyncio.sleep(1)  # 等待1秒后重试

    print(f"❌ 初始化系统环境变量失败，已重试 {max_retries} 次")
    return False

def initialize_command_config_from_env(db: Session):
    """从.env文件初始化命令配置"""
    import os
    from dotenv import load_dotenv

    try:
        # 加载.env文件
        load_dotenv()
        # 定义配置映射
        env_config_mapping = {
            "PYTHON_COMMAND": ("python_command", "Python脚本执行命令"),
            "NODEJS_COMMAND": ("nodejs_command", "Node.js脚本执行命令"),
            "PYTHON_PACKAGE_MANAGER": ("python_package_manager", "Python包管理器"),
            "NODEJS_PACKAGE_MANAGER": ("nodejs_package_manager", "Node.js包管理器")
        }

        updated_configs = []

        # 遍历配置映射，检查.env文件中是否有对应的配置
        for env_key, (config_key, description) in env_config_mapping.items():
            env_value = os.getenv(env_key)
            if env_value and env_value.strip():
                # 检查数据库中是否已存在该配置
                existing_config = get_system_config(db, config_key)
                if not existing_config:
                    # 只有当数据库中不存在该配置时才从.env文件设置
                    set_system_config(db, config_key, env_value.strip(), description)
                    updated_configs.append(f"{config_key}={env_value.strip()}")
                    print(f"✅ 从.env文件设置命令配置: {config_key} = {env_value.strip()}")

        if updated_configs:
            print(f"✅ 已从.env文件初始化 {len(updated_configs)} 个命令配置")
        else:
            print("ℹ️ .env文件中未找到命令配置或配置已存在")

    except Exception as e:
        print(f"⚠️ 从.env文件初始化命令配置失败: {str(e)}")

def get_system_config(db: Session, key: str, default_value: Optional[str] = None) -> Optional[str]:
    """获取系统配置"""
    config = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
    if config:
        return str(config.config_value)
    return default_value

def set_system_config(db: Session, key: str, value: str, description: Optional[str] = None):
    """设置系统配置"""
    config = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
    if config:
        config.config_value = value
        if description:
            config.description = description
    else:
        config = SystemConfig(
            config_key=key,
            config_value=value,
            description=description
        )
        db.add(config)
    db.commit()

def compare_versions(current: str, latest: str) -> bool:
    """比较版本号，如果latest版本更高则返回True"""
    try:
        # 移除版本号前的'v'字符
        current = current.lstrip('v')
        latest = latest.lstrip('v')

        # 分割版本号
        current_parts = [int(x) for x in current.split('.')]
        latest_parts = [int(x) for x in latest.split('.')]

        # 补齐版本号长度
        max_len = max(len(current_parts), len(latest_parts))
        current_parts.extend([0] * (max_len - len(current_parts)))
        latest_parts.extend([0] * (max_len - len(latest_parts)))

        # 比较版本号
        for i in range(max_len):
            if latest_parts[i] > current_parts[i]:
                return True
            elif latest_parts[i] < current_parts[i]:
                return False

        return False
    except Exception:
        return False

@router.get("/check-version", response_model=VersionCheckResponse)
async def check_version_update(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """检查版本更新"""
    try:
        # 获取当前版本
        version = db.query(SystemVersion).filter(SystemVersion.is_current == True).first()
        if not version:
            # 使用配置文件中的版本信息
            current_version = get_current_version()
            current_description = get_version_description()
            version = SystemVersion(version=current_version, description=current_description, is_current=True)
            db.add(version)
            db.commit()
            db.refresh(version)

        current_version = str(version.version)

        # 获取或创建系统UUID
        system_uuid = get_or_create_system_uuid(db)

        # 获取系统信息用于统计
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        # 获取Node.js版本
        nodejs_version = "未安装"
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            nodejs_version = result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            nodejs_version = "未安装或未找到"

        # 获取系统信息
        system_info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor()
        }

        # 准备发送到服务器的数据
        payload = {
            "system_uuid": system_uuid,
            "current_version": current_version,
            "python_version": python_version,
            "nodejs_version": nodejs_version,
            "os_platform": system_info["platform"],
            "platform_version": system_info["platform_version"],
            "architecture": system_info["architecture"],
            "processor": system_info["processor"]
        }

        # 发送请求到远程API（关闭SSL验证）
        try:
            response = requests.post(
                "https://pinchy.maishazi.cn/api/update/check/upgrade/",
                json=payload,
                timeout=10
                # verify=False
            )

            if response.status_code == 200:
                data = response.json()
                latest_version = data.get("version", current_version)
                has_update = compare_versions(current_version, latest_version)

                return VersionCheckResponse(
                    current_version=current_version,
                    latest_version=latest_version,
                    has_update=has_update,
                    upgrade_date=data.get("upgrade_date"),
                    download_url=data.get("download_url"),
                    upgrade_info=data.get("upgrade_info"),
                    created_at=version.created_at.isoformat() if version.created_at is not None else None
                )
            else:
                # 请求失败，返回当前版本信息
                return VersionCheckResponse(
                    current_version=current_version,
                    latest_version=current_version,
                    has_update=False,
                    created_at=version.created_at.isoformat() if version.created_at is not None else None
                )
        except Exception as e:
            print(f"版本检查请求失败: {str(e)}")
            # 网络请求失败，返回当前版本信息
            return VersionCheckResponse(
                current_version=current_version,
                latest_version=current_version,
                has_update=False,
                created_at=version.created_at.isoformat() if version.created_at is not None else None
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检查版本更新失败: {str(e)}")

@router.get("/log-cleanup", response_model=LogCleanupSettings)
async def get_log_cleanup_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取日志清理设置"""
    try:
        # 从数据库读取配置
        enabled_str = get_system_config(db, "log_cleanup_enabled", "false")
        retention_days_str = get_system_config(db, "log_cleanup_retention_days", "7")

        enabled = enabled_str.lower() == "true" if enabled_str else False
        retention_days = int(retention_days_str) if retention_days_str and retention_days_str.isdigit() else 7

        return LogCleanupSettings(enabled=enabled, retention_days=retention_days)
    except Exception as e:
        # 出错时返回默认设置
        print(f"获取日志清理设置失败: {str(e)}")
        return LogCleanupSettings(enabled=False, retention_days=7)

@router.post("/log-cleanup")
async def save_log_cleanup_settings(
    settings: LogCleanupSettings,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """保存日志清理设置"""
    try:
        # 保存设置到数据库
        set_system_config(db, "log_cleanup_enabled", str(settings.enabled).lower(), "日志自动清理开关")
        set_system_config(db, "log_cleanup_retention_days", str(settings.retention_days), "日志保留天数")

        return {"message": "日志清理设置已保存", "settings": settings}
    except Exception as e:
        print(f"保存日志清理设置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存设置失败: {str(e)}")

@router.post("/clear-all-logs")
async def clear_all_logs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """清空所有日志"""
    try:
        # 删除所有日志记录
        deleted_count = db.query(TaskLog).delete()
        db.commit()

        return {"message": f"已清空所有日志，共删除 {deleted_count} 条记录"}
    except Exception as e:
        print(f"清空日志失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"清空日志失败: {str(e)}")

@router.post("/cleanup-old-logs")
async def cleanup_old_logs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """根据设置清理旧日志"""
    try:
        # 获取清理设置
        enabled_str = get_system_config(db, "log_cleanup_enabled", "false")
        retention_days_str = get_system_config(db, "log_cleanup_retention_days", "7")

        enabled = enabled_str.lower() == "true" if enabled_str else False
        retention_days = int(retention_days_str) if retention_days_str and retention_days_str.isdigit() else 7

        if not enabled:
            return {"message": "日志自动清理未启用"}

        # 计算截止日期
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        # 删除旧日志
        deleted_count = db.query(TaskLog).filter(TaskLog.created_at < cutoff_date).delete()
        db.commit()

        return {"message": f"已清理 {retention_days} 天前的日志，共删除 {deleted_count} 条记录"}
    except Exception as e:
        print(f"清理旧日志失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"清理旧日志失败: {str(e)}")

@router.get("/security-config", response_model=SecurityConfigResponse)
async def get_security_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取安全配置"""
    # 获取可用的通知方式
    available_notifications = []
    notification_configs = db.query(NotificationConfig).filter(
        NotificationConfig.is_active == True
    ).all()

    for config in notification_configs:
        # 格式化显示名称，类似通知服务页面的格式
        display_name = config.name
        if config.name == "email":
            email = config.config.get("smtp_user", "")
            if email:
                masked_email = email[:3] + "***" + email[-6:] if len(email) > 9 else email
                display_name = f"邮箱（{masked_email}）"
        elif config.name == "pushplus":
            token = config.config.get("token", "")
            if token:
                masked_token = token[:4] + "******" + token[-4:] if len(token) > 8 else token
                display_name = f"PushPlus（{masked_token}）"
        elif config.name == "wxpusher":
            app_token = config.config.get("app_token", "")
            if app_token:
                masked_token = app_token[:4] + "******" + app_token[-4:] if len(app_token) > 8 else app_token
                display_name = f"WxPusher（{masked_token}）"

        available_notifications.append({
            "value": config.name,
            "label": display_name
        })

    return SecurityConfigResponse(
        captcha_enabled=security_manager.is_captcha_enabled(db),
        ip_blocking_enabled=security_manager.is_ip_blocking_enabled(db),
        mfa_enabled=security_manager.is_mfa_enabled(db),
        mfa_notification_type=security_manager.get_mfa_notification_type(db),
        available_notifications=available_notifications
    )

@router.post("/security-config")
async def update_security_config(
    config_data: SecurityConfigRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新安全配置"""
    # 更新验证码设置
    security_manager.set_security_config(
        db, "captcha_enabled",
        "true" if config_data.captcha_enabled else "false",
        "是否启用验证码"
    )

    # 更新IP阻止设置
    security_manager.set_security_config(
        db, "ip_blocking_enabled",
        "true" if config_data.ip_blocking_enabled else "false",
        "是否启用IP阻止"
    )

    # 更新多因素认证设置
    security_manager.set_security_config(
        db, "mfa_enabled",
        "true" if config_data.mfa_enabled else "false",
        "是否启用多因素认证"
    )

    # 更新MFA通知类型
    if config_data.mfa_enabled and config_data.mfa_notification_type:
        # 验证通知类型是否有效
        notification_config = db.query(NotificationConfig).filter(
            NotificationConfig.name == config_data.mfa_notification_type,
            NotificationConfig.is_active == True
        ).first()

        if not notification_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="选择的通知方式不存在或未激活"
            )

        security_manager.set_security_config(
            db, "mfa_notification_type",
            config_data.mfa_notification_type,
            "多因素认证通知类型"
        )
    elif not config_data.mfa_enabled:
        # 如果禁用MFA，清除通知类型
        security_manager.set_security_config(
            db, "mfa_notification_type",
            "",
            "多因素认证通知类型"
        )

    return {"message": "安全配置更新成功"}

@router.get("/command-config", response_model=CommandConfigResponse)
async def get_command_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取命令配置"""
    try:
        python_command = get_system_config(db, "python_command", "python")
        nodejs_command = get_system_config(db, "nodejs_command", "node")
        python_package_manager = get_system_config(db, "python_package_manager", "pip")
        nodejs_package_manager = get_system_config(db, "nodejs_package_manager", "npm")

        return CommandConfigResponse(
            python_command=python_command,
            nodejs_command=nodejs_command,
            python_package_manager=python_package_manager,
            nodejs_package_manager=nodejs_package_manager
        )
    except Exception as e:
        print(f"获取命令配置失败: {str(e)}")
        # 返回默认配置
        return CommandConfigResponse(
            python_command="python",
            nodejs_command="node",
            python_package_manager="pip",
            nodejs_package_manager="npm"
        )

@router.post("/command-config")
async def save_command_config(
    config_data: CommandConfigRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """保存命令配置"""
    try:
        # 保存Python命令配置
        set_system_config(
            db,
            "python_command",
            config_data.python_command.strip(),
            "Python脚本执行命令"
        )

        # 保存Node.js命令配置
        set_system_config(
            db,
            "nodejs_command",
            config_data.nodejs_command.strip(),
            "Node.js脚本执行命令"
        )

        # 保存Python包管理器配置
        set_system_config(
            db,
            "python_package_manager",
            config_data.python_package_manager.strip(),
            "Python包管理器"
        )

        # 保存Node.js包管理器配置
        set_system_config(
            db,
            "nodejs_package_manager",
            config_data.nodejs_package_manager.strip(),
            "Node.js包管理器"
        )

        return {"message": "命令配置保存成功"}
    except Exception as e:
        print(f"保存命令配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存命令配置失败: {str(e)}")

@router.post("/test-command", response_model=CommandTestResponse)
async def test_command(
    test_data: CommandTestRequest,
    current_user: User = Depends(get_current_user)
):
    """测试命令是否可用"""
    try:
        command = test_data.command.strip()
        if not command:
            return CommandTestResponse(
                success=False,
                message="命令不能为空"
            )

        # 根据命令类型执行不同的测试
        if test_data.command_type == "python":
            # 测试Python命令
            result = subprocess.run(
                [command, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                version = result.stdout.strip()
                return CommandTestResponse(
                    success=True,
                    message=f"Python命令测试成功",
                    version=version
                )
            else:
                return CommandTestResponse(
                    success=False,
                    message=f"Python命令测试失败: {result.stderr.strip() or '未知错误'}"
                )

        elif test_data.command_type == "nodejs":
            # 测试Node.js命令
            result = subprocess.run(
                [command, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                version = result.stdout.strip()
                return CommandTestResponse(
                    success=True,
                    message=f"Node.js命令测试成功",
                    version=version
                )
            else:
                return CommandTestResponse(
                    success=False,
                    message=f"Node.js命令测试失败: {result.stderr.strip() or '未知错误'}"
                )
        else:
            return CommandTestResponse(
                success=False,
                message="不支持的命令类型"
            )

    except subprocess.TimeoutExpired:
        return CommandTestResponse(
            success=False,
            message="命令执行超时"
        )
    except FileNotFoundError:
        return CommandTestResponse(
            success=False,
            message="命令未找到，请检查路径是否正确"
        )
    except Exception as e:
        return CommandTestResponse(
            success=False,
            message=f"测试失败: {str(e)}"
        )

@router.post("/test-package-manager", response_model=PackageManagerTestResponse)
async def test_package_manager(
    test_data: PackageManagerTestRequest,
    current_user: User = Depends(get_current_user)
):
    """测试包管理器是否可用"""
    try:
        manager = test_data.manager.strip()
        if not manager:
            return PackageManagerTestResponse(
                success=False,
                message="包管理器不能为空"
            )

        # 根据管理器类型执行不同的测试
        import platform
        is_windows = platform.system().lower() == 'windows'

        if test_data.manager_type == "python":
            if manager == "pip":
                result = subprocess.run(
                    [manager, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=is_windows
                )
            elif manager == "conda":
                result = subprocess.run(
                    [manager, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=is_windows
                )
            elif manager == "poetry":
                result = subprocess.run(
                    [manager, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=is_windows
                )
            else:
                return PackageManagerTestResponse(
                    success=False,
                    message=f"不支持的Python包管理器: {manager}"
                )

            if result.returncode == 0:
                version = result.stdout.strip()
                return PackageManagerTestResponse(
                    success=True,
                    message=f"{manager}包管理器测试成功",
                    version=version
                )
            else:
                return PackageManagerTestResponse(
                    success=False,
                    message=f"{manager}包管理器测试失败: {result.stderr.strip() or '未知错误'}"
                )

        elif test_data.manager_type == "nodejs":
            import platform
            is_windows = platform.system().lower() == 'windows'

            if manager == "npm":
                result = subprocess.run(
                    [manager, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=is_windows
                )
            elif manager == "yarn":
                result = subprocess.run(
                    [manager, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=is_windows
                )
            elif manager == "pnpm":
                result = subprocess.run(
                    [manager, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=is_windows
                )
            else:
                return PackageManagerTestResponse(
                    success=False,
                    message=f"不支持的Node.js包管理器: {manager}"
                )

            if result.returncode == 0:
                version = result.stdout.strip()
                return PackageManagerTestResponse(
                    success=True,
                    message=f"{manager}包管理器测试成功",
                    version=version
                )
            else:
                return PackageManagerTestResponse(
                    success=False,
                    message=f"{manager}包管理器测试失败: {result.stderr.strip() or '未知错误'}"
                )
        else:
            return PackageManagerTestResponse(
                success=False,
                message="不支持的包管理器类型"
            )

    except subprocess.TimeoutExpired:
        return PackageManagerTestResponse(
            success=False,
            message="包管理器测试超时"
        )
    except FileNotFoundError:
        return PackageManagerTestResponse(
            success=False,
            message="包管理器未找到，请检查是否已安装"
        )
    except Exception as e:
        return PackageManagerTestResponse(
            success=False,
            message=f"测试失败: {str(e)}"
        )

@router.get("/timezone-config", response_model=TimezoneConfigResponse)
async def get_timezone_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取时区配置"""
    try:
        # 获取当前时区
        current_timezone = get_system_timezone(db)

        # 获取可用时区列表
        available_timezones = []
        for tz_name, tz_display in get_available_timezones():
            available_timezones.append(TimezoneInfo(
                name=tz_name,
                display_name=tz_display,
                offset=get_timezone_offset(tz_name)
            ))

        # 获取当前时区的显示信息
        current_display = next(
            (tz.display_name for tz in available_timezones if tz.name == current_timezone),
            current_timezone
        )
        current_offset = get_timezone_offset(current_timezone)

        return TimezoneConfigResponse(
            current_timezone=current_timezone,
            current_timezone_display=current_display,
            current_offset=current_offset,
            available_timezones=available_timezones
        )
    except Exception as e:
        print(f"获取时区配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取时区配置失败: {str(e)}")

@router.post("/timezone-config")
async def update_timezone_config(
    config_data: TimezoneConfigRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新时区配置"""
    try:
        # 验证时区是否有效
        if not validate_timezone(config_data.timezone):
            raise HTTPException(status_code=400, detail="无效的时区名称")

        # 保存时区配置
        if set_system_timezone(db, config_data.timezone):
            return {"message": "时区配置已更新", "timezone": config_data.timezone}
        else:
            raise HTTPException(status_code=400, detail="时区配置更新失败")
    except HTTPException:
        raise
    except Exception as e:
        print(f"更新时区配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新时区配置失败: {str(e)}")

def init_system_version(db: Session):
    """初始化或更新系统版本"""
    current_app_version = get_current_version()
    current_description = get_version_description()

    # 查找当前版本记录
    version = db.query(SystemVersion).filter(SystemVersion.is_current == True).first()

    if not version:
        # 如果没有版本记录，创建新的
        version = SystemVersion(
            version=current_app_version,
            description=current_description,
            is_current=True
        )
        db.add(version)
        db.commit()
        print(f"已初始化系统版本: {current_app_version}")
    else:
        # 如果已有版本记录，检查是否需要更新
        if version.version != current_app_version:
            # 版本号不同，需要更新
            old_version = version.version

            # 将旧版本标记为非当前版本（保留历史记录）
            version.is_current = False

            # 创建新的版本记录
            new_version = SystemVersion(
                version=current_app_version,
                description=current_description,
                is_current=True
            )
            db.add(new_version)
            db.commit()

            print(f"🔄 系统版本已更新: {old_version} → {current_app_version}")

            # 记录版本更新信息
            version_info = get_version_info(current_app_version)
            if version_info:
                print(f"📝 版本更新说明: {version_info.get('description', '')}")
                features = version_info.get('features', [])
                if features:
                    print("✨ 新功能:")
                    for feature in features[:3]:  # 只显示前3个
                        print(f"   - {feature}")
                    if len(features) > 3:
                        print(f"   ... 还有 {len(features) - 3} 个新功能")
        else:
            # 版本号相同，检查描述是否需要更新
            if version.description != current_description:
                version.description = current_description
                db.commit()
                print(f"📝 系统版本描述已更新: {current_app_version}")
            else:
                print(f"✅ 系统版本已是最新: {current_app_version}")

def init_system_uuid(db: Session):
    """初始化系统UUID"""
    system_uuid = db.query(SystemUUID).first()
    if not system_uuid:
        new_uuid = str(uuid.uuid4())
        system_uuid = SystemUUID(uuid=new_uuid)
        db.add(system_uuid)
        db.commit()
        print(f"已初始化系统UUID: {new_uuid}")
    else:
        print(f"系统UUID已存在: {system_uuid.uuid}")

@router.post("/export-backup", response_model=BackupResponse)
async def export_backup(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """导出系统备份"""
    try:
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = os.path.join(temp_dir, "backup")
            os.makedirs(backup_dir, exist_ok=True)

            # 1. 备份scripts目录
            scripts_dir = "scripts"
            if os.path.exists(scripts_dir):
                backup_scripts_dir = os.path.join(backup_dir, "scripts")
                shutil.copytree(scripts_dir, backup_scripts_dir)
                print(f"✅ 已备份scripts目录")

            # 2. 备份数据库（排除system_version表）
            db_backup_path = os.path.join(backup_dir, "database.sql")
            await backup_database(db, db_backup_path)
            print(f"✅ 已备份数据库")

            # 3. 创建.pb文件（实际是tar压缩包）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"pinchy_backup_{timestamp}.pb"
            backup_path = os.path.join(temp_dir, backup_filename)

            with tarfile.open(backup_path, "w:gz") as tar:
                tar.add(backup_dir, arcname=".")

            # 获取文件大小
            file_size = os.path.getsize(backup_path)

            # 移动到静态文件目录供下载
            static_backup_dir = "static/backups"
            os.makedirs(static_backup_dir, exist_ok=True)
            final_backup_path = os.path.join(static_backup_dir, backup_filename)
            shutil.move(backup_path, final_backup_path)

            return BackupResponse(
                message="备份创建成功",
                filename=backup_filename,
                size=file_size
            )

    except Exception as e:
        print(f"❌ 备份失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"备份失败: {str(e)}")

async def backup_database(db: Session, output_path: str):
    """备份数据库到SQL文件（排除system_version表）"""
    try:
        # 获取数据库连接字符串
        db_url = str(db.bind.url)

        if "sqlite" in db_url:
            # SQLite数据库备份
            db_path = db_url.replace("sqlite:///", "")

            # 连接到数据库
            conn = sqlite3.connect(db_path)

            # 获取所有表名（排除system_version）
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'system_version'")
            tables = [row[0] for row in cursor.fetchall()]

            # 生成SQL备份
            with open(output_path, 'w', encoding='utf-8') as f:
                # 写入表结构和数据
                for table in tables:
                    # 获取表结构
                    cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'")
                    create_sql = cursor.fetchone()
                    if create_sql:
                        f.write(f"{create_sql[0]};\n\n")

                    # 获取表数据
                    cursor.execute(f"SELECT * FROM {table}")
                    rows = cursor.fetchall()

                    if rows:
                        # 获取列名
                        cursor.execute(f"PRAGMA table_info({table})")
                        columns = [col[1] for col in cursor.fetchall()]

                        for row in rows:
                            values = []
                            for value in row:
                                if value is None:
                                    values.append("NULL")
                                elif isinstance(value, str):
                                    # 转义单引号
                                    escaped_value = value.replace("'", "''")
                                    values.append(f"'{escaped_value}'")
                                else:
                                    values.append(str(value))

                            f.write(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(values)});\n")
                        f.write("\n")

            conn.close()
            print(f"✅ SQLite数据库备份完成: {len(tables)} 个表")
        else:
            raise HTTPException(status_code=500, detail="暂不支持非SQLite数据库的备份")

    except Exception as e:
        print(f"❌ 数据库备份失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"数据库备份失败: {str(e)}")

@router.get("/download-backup/{filename}")
async def download_backup(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """下载备份文件"""
    try:
        backup_path = os.path.join("static/backups", filename)
        if not os.path.exists(backup_path):
            raise HTTPException(status_code=404, detail="备份文件不存在")

        return FileResponse(
            path=backup_path,
            filename=filename,
            media_type='application/octet-stream'
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")

@router.post("/import-backup", response_model=RestoreResponse)
async def import_backup(
    backup_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """导入备份文件并恢复系统"""
    try:
        # 验证文件扩展名
        if not backup_file.filename.endswith('.pb'):
            raise HTTPException(status_code=400, detail="无效的备份文件格式，请选择.pb文件")

        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 保存上传的文件
            backup_path = os.path.join(temp_dir, backup_file.filename)
            with open(backup_path, "wb") as buffer:
                content = await backup_file.read()
                buffer.write(content)

            # 解压备份文件
            extract_dir = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)

            try:
                with tarfile.open(backup_path, "r:gz") as tar:
                    tar.extractall(extract_dir)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"备份文件损坏或格式错误: {str(e)}")

            files_restored = 0
            tables_restored = 0

            # 1. 恢复scripts目录
            scripts_backup_path = os.path.join(extract_dir, "scripts")
            if os.path.exists(scripts_backup_path):
                scripts_dir = "scripts"
                if os.path.exists(scripts_dir):
                    # 备份现有scripts目录
                    backup_existing_scripts = f"scripts_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    shutil.move(scripts_dir, backup_existing_scripts)
                    print(f"✅ 已备份现有scripts目录到: {backup_existing_scripts}")

                shutil.copytree(scripts_backup_path, scripts_dir)
                files_restored = count_files_in_directory(scripts_dir)
                print(f"✅ 已恢复scripts目录，共 {files_restored} 个文件")

            # 2. 恢复数据库
            db_backup_path = os.path.join(extract_dir, "database.sql")
            if os.path.exists(db_backup_path):
                tables_restored = await restore_database(db, db_backup_path)
                print(f"✅ 已恢复数据库，共 {tables_restored} 个表")

            return RestoreResponse(
                message="备份恢复成功，系统将自动注销以刷新会话",
                files_restored=files_restored,
                tables_restored=tables_restored
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 恢复失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"恢复失败: {str(e)}")

async def restore_database(db: Session, sql_file_path: str):
    """从SQL文件恢复数据库（保留system_version表）"""
    try:
        # 获取数据库连接字符串
        db_url = str(db.bind.url)

        if "sqlite" in db_url:
            db_path = db_url.replace("sqlite:///", "")

            # 读取SQL文件
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            # 连接到数据库
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # 获取当前system_version表的数据（需要保留）
            system_version_data = []
            try:
                cursor.execute("SELECT * FROM system_version")
                system_version_data = cursor.fetchall()
                print(f"✅ 已保存system_version表数据: {len(system_version_data)} 条记录")
            except sqlite3.OperationalError:
                print("ℹ️ system_version表不存在，跳过保存")

            # 获取需要删除的表（排除system_version）
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'system_version'")
            tables_to_drop = [row[0] for row in cursor.fetchall()]

            # 删除现有表（排除system_version）
            for table in tables_to_drop:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")

            # 执行恢复SQL
            cursor.executescript(sql_content)

            # 恢复system_version表数据
            if system_version_data:
                try:
                    # 如果备份中包含system_version表，先删除
                    cursor.execute("DROP TABLE IF EXISTS system_version")

                    # 重新创建system_version表
                    cursor.execute("""
                        CREATE TABLE system_version (
                            id INTEGER PRIMARY KEY,
                            version VARCHAR(20) NOT NULL,
                            description TEXT,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            is_current BOOLEAN DEFAULT 1
                        )
                    """)

                    # 插入保存的数据
                    for row in system_version_data:
                        placeholders = ','.join(['?' for _ in row])
                        cursor.execute(f"INSERT INTO system_version VALUES ({placeholders})", row)

                    print(f"✅ 已恢复system_version表数据")
                except Exception as e:
                    print(f"⚠️ 恢复system_version表失败: {str(e)}")

            conn.commit()
            conn.close()

            # 获取恢复的表数量
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            conn.close()

            return table_count
        else:
            raise HTTPException(status_code=500, detail="暂不支持非SQLite数据库的恢复")

    except Exception as e:
        print(f"❌ 数据库恢复失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"数据库恢复失败: {str(e)}")

def count_files_in_directory(directory: str) -> int:
    """递归计算目录中的文件数量"""
    count = 0
    for root, dirs, files in os.walk(directory):
        count += len(files)
    return count
