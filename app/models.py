"""
数据库模型定义
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, default="admin")
    password_hash = Column(String(255), nullable=False)
    color_scheme = Column(String(20), default="blue")  # 用户配色方案
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Task(Base):
    """任务表"""
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    script_path = Column(String(500), nullable=False)
    script_type = Column(String(20), nullable=False)  # python 或 nodejs
    cron_expression = Column(String(100), nullable=False)
    environment_vars = Column(JSON, default={})  # 环境变量
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class TaskLog(Base):
    """任务执行日志表"""
    __tablename__ = "task_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, nullable=False)
    task_name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)  # running, success, failed
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True))
    output = Column(Text)
    error_output = Column(Text)
    exit_code = Column(Integer)

class EnvironmentVariable(Base):
    """环境变量表"""
    __tablename__ = "environment_variables"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(Text)
    is_system = Column(Boolean, default=False)  # 是否为系统级变量
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class PackageInfo(Base):
    """包信息表"""
    __tablename__ = "packages"

    id = Column(Integer, primary_key=True, index=True)
    package_type = Column(String(20), nullable=False)  # python 或 nodejs
    package_name = Column(String(100), nullable=False)
    version = Column(String(50))
    installed_at = Column(DateTime(timezone=True), server_default=func.now())

class NotificationConfig(Base):
    """通知配置表"""
    __tablename__ = "notification_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)  # email, pushplus, wxpusher
    config = Column(JSON, nullable=False)  # 配置信息
    is_active = Column(Boolean, default=False)  # 是否激活
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class TaskNotificationConfig(Base):
    """任务通知配置表"""
    __tablename__ = "task_notification_configs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, nullable=False)
    notification_type = Column(String(50))  # 通知类型：email, pushplus, wxpusher
    error_only = Column(Boolean, default=False)  # 是否只推送错误
    keywords = Column(Text)  # 关键词列表，逗号分隔
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
class SystemConfig(Base):
    """系统配置表"""
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(Text, nullable=False)
    description = Column(Text)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class SystemVersion(Base):
    """系统版本表"""
    __tablename__ = "system_version"

    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(20), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_current = Column(Boolean, default=True)

class SystemUUID(Base):
    """系统UUID标识表"""
    __tablename__ = "system_uuid"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ApiDebugConfig(Base):
    """接口调试配置表"""
    __tablename__ = "api_debug_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # 配置名称
    description = Column(Text)  # 描述
    method = Column(String(10), nullable=False, default="GET")  # HTTP方法
    url = Column(Text, nullable=False)  # 请求URL
    headers = Column(JSON, default={})  # 请求头
    payload = Column(Text)  # 请求体
    notification_type = Column(String(50))  # 通知类型
    notification_enabled = Column(Boolean, default=False)  # 是否启用通知
    notification_condition = Column(String(20), default="always")  # 通知条件：always, success, error
    cron_expression = Column(String(100))  # 定时表达式
    is_active = Column(Boolean, default=False)  # 是否启用定时
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ApiDebugLog(Base):
    """接口调试执行日志表"""
    __tablename__ = "api_debug_logs"

    id = Column(Integer, primary_key=True, index=True)
    config_id = Column(Integer, nullable=False)  # 配置ID
    config_name = Column(String(100), nullable=False)  # 配置名称
    method = Column(String(10), nullable=False)  # HTTP方法
    url = Column(Text, nullable=False)  # 请求URL
    request_headers = Column(JSON)  # 请求头
    request_payload = Column(Text)  # 请求体
    response_status = Column(Integer)  # 响应状态码
    response_headers = Column(JSON)  # 响应头
    response_body = Column(Text)  # 响应体
    response_time = Column(Integer)  # 响应时间(毫秒)
    error_message = Column(Text)  # 错误信息
    status = Column(String(20), nullable=False)  # 执行状态：success, error
    notification_sent = Column(Boolean, default=False)  # 是否已发送通知
    start_time = Column(DateTime(timezone=True), server_default=func.now())

class ScriptSubscription(Base):
    """脚本订阅表"""
    __tablename__ = "script_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # 订阅名称
    description = Column(Text)  # 描述
    git_url = Column(Text, nullable=False)  # Git仓库URL
    save_directory = Column(String(500), nullable=False)  # 保存目录
    file_extensions = Column(JSON, default=[])  # 允许的文件扩展名列表
    exclude_patterns = Column(JSON, default=[])  # 排除的文件和文件夹名模式列表
    include_folders = Column(Boolean, default=True)  # 是否包含文件夹
    include_subfolders = Column(Boolean, default=True)  # 是否包含子文件夹内容
    use_proxy = Column(Boolean, default=False)  # 是否使用代理
    sync_delete_removed_files = Column(Boolean, default=False)  # 是否同步删除移除的文件
    cron_expression = Column(String(100), nullable=False)  # 定时表达式
    notification_enabled = Column(Boolean, default=False)  # 是否启用通知
    notification_type = Column(String(50))  # 通知类型
    is_active = Column(Boolean, default=True)  # 是否启用
    last_sync_time = Column(DateTime(timezone=True))  # 最后同步时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class LoginAttempt(Base):
    """登录尝试记录表"""
    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(45), nullable=False, index=True)  # IP地址，支持IPv6
    username = Column(String(50), nullable=False)  # 尝试登录的用户名
    success = Column(Boolean, default=False)  # 是否成功
    attempt_time = Column(DateTime(timezone=True), server_default=func.now())  # 尝试时间
    user_agent = Column(Text)  # 用户代理

class SecurityConfig(Base):
    """安全配置表"""
    __tablename__ = "security_config"

    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(100), unique=True, nullable=False)  # 配置键
    config_value = Column(Text, nullable=False)  # 配置值
    description = Column(Text)  # 描述
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class MFACode(Base):
    """多因素认证码表"""
    __tablename__ = "mfa_codes"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(45), nullable=False, index=True)  # IP地址
    code = Column(String(6), nullable=False)  # 6位验证码
    expires_at = Column(DateTime(timezone=True), nullable=False)  # 过期时间
    used = Column(Boolean, default=False)  # 是否已使用
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # 创建时间
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class SubscriptionFile(Base):
    """订阅文件表"""
    __tablename__ = "subscription_files"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, nullable=False)  # 订阅ID
    file_path = Column(String(1000), nullable=False)  # 文件相对路径
    file_md5 = Column(String(32), nullable=False)  # 文件MD5值
    file_size = Column(Integer, default=0)  # 文件大小
    is_new = Column(Boolean, default=False)  # 是否为新文件
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class SubscriptionLog(Base):
    """订阅执行日志表"""
    __tablename__ = "subscription_logs"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, nullable=False)  # 订阅ID
    subscription_name = Column(String(100), nullable=False)  # 订阅名称
    status = Column(String(20), nullable=False)  # 执行状态：running, success, error
    message = Column(Text)  # 执行消息
    files_updated = Column(Integer, default=0)  # 更新文件数量
    files_added = Column(Integer, default=0)  # 新增文件数量
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
