"""
安全相关功能
"""
import os
import random
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import Request
from app.models import LoginAttempt, SecurityConfig, MFACode

class SecurityManager:
    """安全管理器"""

    def __init__(self):
        # 从环境变量读取配置，如果没有设置则使用默认值
        self.max_login_attempts = int(os.getenv('SECURITY_MAX_LOGIN_ATTEMPTS', '5'))  # 最大登录尝试次数
        self.lockout_duration = int(os.getenv('SECURITY_LOCKOUT_DURATION', '30'))  # 锁定时间（分钟）
        self.mfa_code_expiry = int(os.getenv('SECURITY_MFA_CODE_EXPIRY', '5'))  # MFA验证码过期时间（分钟）
    
    def get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        # 优先从X-Forwarded-For头获取真实IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # 从X-Real-IP头获取
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # 最后使用客户端IP
        return request.client.host if request.client else "unknown"
    
    def record_login_attempt(self, db: Session, ip_address: str, username: str, 
                           success: bool, user_agent: str = None):
        """记录登录尝试"""
        attempt = LoginAttempt(
            ip_address=ip_address,
            username=username,
            success=success,
            user_agent=user_agent
        )
        db.add(attempt)
        db.commit()
    
    def get_failed_attempts_count(self, db: Session, ip_address: str,
                                username: str, minutes: Optional[int] = None) -> int:
        """获取指定时间内的失败登录次数"""
        if minutes is None:
            minutes = self.lockout_duration
        since_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        count = db.query(LoginAttempt).filter(
            LoginAttempt.ip_address == ip_address,
            LoginAttempt.username == username,
            LoginAttempt.success == False,
            LoginAttempt.attempt_time >= since_time
        ).count()
        
        return count
    
    def is_ip_locked(self, db: Session, ip_address: str, username: str) -> bool:
        """检查IP是否被锁定"""
        failed_count = self.get_failed_attempts_count(db, ip_address, username)
        return failed_count >= self.max_login_attempts

    def get_lockout_remaining_time(self, db: Session, ip_address: str, username: str) -> int:
        """获取IP锁定剩余时间（分钟），如果未锁定返回0"""
        if not self.is_ip_locked(db, ip_address, username):
            return 0

        # 获取最近一次失败登录的时间
        latest_attempt = db.query(LoginAttempt).filter(
            LoginAttempt.ip_address == ip_address,
            LoginAttempt.username == username,
            LoginAttempt.success == False
        ).order_by(LoginAttempt.attempt_time.desc()).first()

        if not latest_attempt:
            return 0

        # 计算锁定结束时间
        lockout_end_time = latest_attempt.attempt_time + timedelta(minutes=self.lockout_duration)
        remaining_time = lockout_end_time - datetime.utcnow()

        # 返回剩余分钟数，最小为0
        return max(0, int(remaining_time.total_seconds() / 60))
    
    def get_security_config(self, db: Session, key: str, default_value: str = None) -> Optional[str]:
        """获取安全配置"""
        config = db.query(SecurityConfig).filter(SecurityConfig.config_key == key).first()
        if config:
            return config.config_value
        return default_value
    
    def set_security_config(self, db: Session, key: str, value: str, description: str = None):
        """设置安全配置"""
        config = db.query(SecurityConfig).filter(SecurityConfig.config_key == key).first()
        if config:
            config.config_value = value
            if description:
                config.description = description
        else:
            config = SecurityConfig(
                config_key=key,
                config_value=value,
                description=description
            )
            db.add(config)
        db.commit()
    
    def is_captcha_enabled(self, db: Session) -> bool:
        """检查是否启用验证码"""
        return self.get_security_config(db, "captcha_enabled", "false") == "true"
    
    def is_ip_blocking_enabled(self, db: Session) -> bool:
        """检查是否启用IP阻止"""
        return self.get_security_config(db, "ip_blocking_enabled", "false") == "true"
    
    def is_mfa_enabled(self, db: Session) -> bool:
        """检查是否启用多因素认证"""
        return self.get_security_config(db, "mfa_enabled", "false") == "true"
    
    def get_mfa_notification_type(self, db: Session) -> Optional[str]:
        """获取MFA通知类型"""
        return self.get_security_config(db, "mfa_notification_type")
    
    def generate_mfa_code(self) -> str:
        """生成6位数字验证码"""
        return ''.join(random.choices(string.digits, k=6))
    
    def create_mfa_code(self, db: Session, ip_address: str) -> str:
        """创建MFA验证码"""
        # 删除该IP的旧验证码
        db.query(MFACode).filter(MFACode.ip_address == ip_address).delete()
        
        # 生成新验证码
        code = self.generate_mfa_code()
        expires_at = datetime.utcnow() + timedelta(minutes=self.mfa_code_expiry)
        
        mfa_code = MFACode(
            ip_address=ip_address,
            code=code,
            expires_at=expires_at
        )
        db.add(mfa_code)
        db.commit()
        
        return code
    
    def verify_mfa_code(self, db: Session, ip_address: str, code: str) -> bool:
        """验证MFA验证码"""
        mfa_code = db.query(MFACode).filter(
            MFACode.ip_address == ip_address,
            MFACode.code == code,
            MFACode.used == False,
            MFACode.expires_at > datetime.utcnow()
        ).first()
        
        if mfa_code:
            # 标记为已使用
            mfa_code.used = True
            db.commit()
            return True
        
        return False
    
    def can_send_mfa_code(self, db: Session, ip_address: str) -> bool:
        """检查是否可以发送MFA验证码（1分钟限制）"""
        one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
        
        recent_code = db.query(MFACode).filter(
            MFACode.ip_address == ip_address,
            MFACode.created_at > one_minute_ago
        ).first()
        
        return recent_code is None
    
    def cleanup_expired_codes(self, db: Session):
        """清理过期的验证码"""
        db.query(MFACode).filter(MFACode.expires_at < datetime.utcnow()).delete()
        db.commit()
    
    def cleanup_old_login_attempts(self, db: Session, days: int = 30):
        """清理旧的登录尝试记录"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        db.query(LoginAttempt).filter(LoginAttempt.attempt_time < cutoff_date).delete()
        db.commit()

# 全局安全管理器实例
security_manager = SecurityManager()
