"""
时区管理工具模块
"""
import pytz
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

def get_system_timezone(db: Session) -> str:
    """获取系统配置的时区，默认为中国时区"""
    from app.routers.settings import get_system_config
    return get_system_config(db, "system_timezone", "Asia/Shanghai")

def set_system_timezone(db: Session, timezone_name: str):
    """设置系统时区"""
    from app.routers.settings import set_system_config
    # 验证时区是否有效
    try:
        pytz.timezone(timezone_name)
        set_system_config(db, "system_timezone", timezone_name, "系统时区设置")
        return True
    except pytz.exceptions.UnknownTimeZoneError:
        return False

def get_current_time(db: Session = None) -> datetime:
    """获取当前时区的当前时间"""
    if db is None:
        # 如果没有数据库连接，使用默认时区
        tz = pytz.timezone("Asia/Shanghai")
    else:
        timezone_name = get_system_timezone(db)
        tz = pytz.timezone(timezone_name)
    
    # 获取UTC时间并转换为指定时区
    utc_now = datetime.now(timezone.utc)
    return utc_now.astimezone(tz)

def utc_to_local(utc_dt: datetime, db: Session = None) -> datetime:
    """将UTC时间转换为本地时区时间"""
    if utc_dt is None:
        return None
    
    if db is None:
        # 如果没有数据库连接，使用默认时区
        tz = pytz.timezone("Asia/Shanghai")
    else:
        timezone_name = get_system_timezone(db)
        tz = pytz.timezone(timezone_name)
    
    # 如果datetime对象没有时区信息，假设它是UTC时间
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    
    # 转换为指定时区
    return utc_dt.astimezone(tz)

def local_to_utc(local_dt: datetime, db: Session = None) -> datetime:
    """将本地时区时间转换为UTC时间"""
    if local_dt is None:
        return None
    
    if db is None:
        # 如果没有数据库连接，使用默认时区
        tz = pytz.timezone("Asia/Shanghai")
    else:
        timezone_name = get_system_timezone(db)
        tz = pytz.timezone(timezone_name)
    
    # 如果datetime对象没有时区信息，假设它是本地时区时间
    if local_dt.tzinfo is None:
        local_dt = tz.localize(local_dt)
    
    # 转换为UTC时间
    return local_dt.astimezone(timezone.utc)

def format_datetime(dt: datetime, db: Session = None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化日期时间为本地时区字符串"""
    if dt is None:
        return ""

    if db is None:
        # 如果没有数据库连接，使用默认时区
        tz = pytz.timezone("Asia/Shanghai")
    else:
        timezone_name = get_system_timezone(db)
        tz = pytz.timezone(timezone_name)

    # 判断输入时间的类型并进行相应处理
    if dt.tzinfo is None:
        # 无时区信息的情况：
        # 对于从数据库读取的时间，由于SQLite不支持时区，我们假设它已经是本地时区时间
        # 这是因为我们在存储时使用的是get_current_time(db)，它返回的是本地时区时间
        # 但存储到SQLite后时区信息丢失了
        local_dt = dt  # 直接使用，不进行时区转换
    elif dt.tzinfo == timezone.utc:
        # UTC时间，转换为本地时区
        local_dt = dt.astimezone(tz)
    else:
        # 已经有时区信息，检查是否已经是目标时区
        if str(dt.tzinfo) == str(tz):
            # 已经是目标时区，直接使用
            local_dt = dt
        else:
            # 转换为目标时区
            local_dt = dt.astimezone(tz)

    return local_dt.strftime(format_str)

def get_available_timezones():
    """获取可用的时区列表"""
    # 常用时区列表
    common_timezones = [
        ("Asia/Shanghai", "中国标准时间 (UTC+8)"),
        ("UTC", "协调世界时 (UTC+0)"),
        ("US/Eastern", "美国东部时间 (UTC-5/-4)"),
        ("US/Central", "美国中部时间 (UTC-6/-5)"),
        ("US/Mountain", "美国山地时间 (UTC-7/-6)"),
        ("US/Pacific", "美国太平洋时间 (UTC-8/-7)"),
        ("Europe/London", "英国时间 (UTC+0/+1)"),
        ("Europe/Paris", "欧洲中部时间 (UTC+1/+2)"),
        ("Europe/Berlin", "德国时间 (UTC+1/+2)"),
        ("Europe/Moscow", "莫斯科时间 (UTC+3)"),
        ("Asia/Tokyo", "日本标准时间 (UTC+9)"),
        ("Asia/Seoul", "韩国标准时间 (UTC+9)"),
        ("Asia/Kolkata", "印度标准时间 (UTC+5:30)"),
        ("Asia/Dubai", "阿联酋时间 (UTC+4)"),
        ("Australia/Sydney", "澳大利亚东部时间 (UTC+10/+11)"),
        ("Australia/Melbourne", "澳大利亚东部时间 (UTC+10/+11)"),
        ("Australia/Perth", "澳大利亚西部时间 (UTC+8)"),
        ("Pacific/Auckland", "新西兰时间 (UTC+12/+13)"),
        ("America/New_York", "纽约时间 (UTC-5/-4)"),
        ("America/Los_Angeles", "洛杉矶时间 (UTC-8/-7)"),
        ("America/Chicago", "芝加哥时间 (UTC-6/-5)"),
        ("America/Denver", "丹佛时间 (UTC-7/-6)"),
        ("America/Toronto", "多伦多时间 (UTC-5/-4)"),
        ("America/Vancouver", "温哥华时间 (UTC-8/-7)"),
        ("America/Sao_Paulo", "圣保罗时间 (UTC-3)"),
        ("America/Mexico_City", "墨西哥城时间 (UTC-6/-5)"),
        ("Africa/Cairo", "开罗时间 (UTC+2)"),
        ("Africa/Johannesburg", "约翰内斯堡时间 (UTC+2)"),
    ]
    
    return common_timezones

def get_timezone_offset(timezone_name: str) -> str:
    """获取时区偏移量字符串"""
    try:
        tz = pytz.timezone(timezone_name)
        now = datetime.now(tz)
        offset = now.strftime('%z')
        # 格式化为 +08:00 形式
        if len(offset) == 5:
            return f"{offset[:3]}:{offset[3:]}"
        return offset
    except:
        return "+00:00"

def validate_timezone(timezone_name: str) -> bool:
    """验证时区名称是否有效"""
    try:
        pytz.timezone(timezone_name)
        return True
    except pytz.exceptions.UnknownTimeZoneError:
        return False

# 为了向后兼容，保留原有的函数
def to_local_time(dt, db: Session = None):
    """将UTC时间转换为本地时间（向后兼容）"""
    if dt is None:
        return None
    
    local_dt = utc_to_local(dt, db)
    if local_dt:
        return local_dt.isoformat()
    return None
