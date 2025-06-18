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
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.auth import get_current_user, get_password_hash, verify_password
from app.models import User, SystemVersion, SystemUUID, SystemConfig, TaskLog, NotificationConfig, EnvironmentVariable
from app.security import security_manager

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

@router.get("/system-info", response_model=SystemInfo)
async def get_system_info(current_user: User = Depends(get_current_user)):
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
        
        return SystemInfo(
            python_version=python_version,
            nodejs_version=nodejs_version,
            system_info=system_info
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
        # 如果没有版本记录，创建默认版本
        version = SystemVersion(version="1.25.1", description="Pinchy - Python、Node.js脚本调度执行系统", is_current=True)
        db.add(version)
        db.commit()
        db.refresh(version)

    return {
        "version": version.version,
        "description": version.description
    }

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
            version = SystemVersion(version="1.25.1", description="Pinchy - Python、Node.js脚本调度执行系统", is_current=True)
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

def init_system_version(db: Session):
    """初始化系统版本"""
    version = db.query(SystemVersion).filter(SystemVersion.is_current == True).first()
    if not version:
        version = SystemVersion(version="1.25.1", description="Pinchy - Python、Node.js脚本调度执行系统", is_current=True)
        db.add(version)
        db.commit()
        print("已初始化系统版本: 1.25.1")

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
