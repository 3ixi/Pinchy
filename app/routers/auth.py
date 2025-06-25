"""
认证相关路由
"""
from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.auth import authenticate_user, create_access_token, get_current_user, get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES
from app.models import User, NotificationConfig
from app.security import security_manager
from app.captcha import CaptchaGenerator
from app.notification_service import NotificationService

router = APIRouter(prefix="/api/auth", tags=["认证"])

class LoginRequest(BaseModel):
    username: str
    password: str
    captcha_answer: Optional[str] = None  # 验证码答案
    mfa_code: Optional[str] = None  # 多因素认证码

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class LoginResponse(BaseModel):
    message: str
    user: dict

class CaptchaResponse(BaseModel):
    image_data: str
    session_id: str

class MFACodeRequest(BaseModel):
    pass  # 不需要额外参数，从IP获取

@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    """用户登录"""
    client_ip = security_manager.get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")

    try:
        # 检查IP是否被锁定
        is_ip_locked = security_manager.is_ip_blocking_enabled(db) and security_manager.is_ip_locked(db, client_ip, login_data.username)

        # 如果IP被锁定，但启用了验证码，则允许通过验证码尝试登录
        if is_ip_locked:
            if not security_manager.is_captcha_enabled(db):
                # 没有启用验证码，直接阻止
                security_manager.record_login_attempt(db, client_ip, login_data.username, False, user_agent)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="登录失败次数过多，IP已被锁定，请稍后再试",
                )
            elif not login_data.captcha_answer:
                # 启用了验证码但没有提供验证码
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="IP已被锁定，请输入验证码",
                )

        # 检查是否需要验证码（失败次数>=5次且启用了验证码）
        failed_attempts = security_manager.get_failed_attempts_count(db, client_ip, login_data.username)
        need_captcha = security_manager.is_captcha_enabled(db) and failed_attempts >= 5

        if need_captcha:
            if not login_data.captcha_answer:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="请输入验证码",
                )

            # 验证验证码
            stored_answer = security_manager.get_security_config(db, f"captcha_answer_{client_ip}")
            if not stored_answer or str(login_data.captcha_answer) != stored_answer:
                security_manager.record_login_attempt(db, client_ip, login_data.username, False, user_agent)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="验证码错误",
                )

        # 验证用户名密码
        user = authenticate_user(db, login_data.username, login_data.password)
        if not user:
            security_manager.record_login_attempt(db, client_ip, login_data.username, False, user_agent)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
            )

        # 检查多因素认证（如果启用）
        if security_manager.is_mfa_enabled(db):
            if not login_data.mfa_code:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="请输入多因素认证码",
                )

            if not security_manager.verify_mfa_code(db, client_ip, login_data.mfa_code):
                security_manager.record_login_attempt(db, client_ip, login_data.username, False, user_agent)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="多因素认证码错误或已过期",
                )

        # 记录成功登录
        security_manager.record_login_attempt(db, client_ip, login_data.username, True, user_agent)

        # 获取系统UUID用于增强JWT安全性
        from app.routers.settings import get_or_create_system_uuid
        try:
            system_uuid = get_or_create_system_uuid(db)
        except Exception:
            system_uuid = None

        # 创建访问令牌
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username},
            expires_delta=access_token_expires,
            system_uuid=system_uuid
        )

        # 设置Cookie
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            samesite="lax"
        )

        return LoginResponse(
            message="登录成功",
            user={
                "id": user.id,
                "username": user.username,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        security_manager.record_login_attempt(db, client_ip, login_data.username, False, user_agent)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录过程中发生错误",
        )

@router.post("/logout")
async def logout(response: Response, current_user: User = Depends(get_current_user)):
    """用户登出"""
    response.delete_cookie(key="access_token")
    return {"message": "登出成功"}

@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }

@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """修改密码"""
    from app.auth import verify_password
    
    # 验证旧密码
    if not verify_password(password_data.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误"
        )
    
    # 更新密码
    current_user.password_hash = get_password_hash(password_data.new_password)
    db.commit()
    
    return {"message": "密码修改成功"}

@router.get("/captcha")
async def get_captcha(request: Request, db: Session = Depends(get_db)):
    """获取验证码"""
    client_ip = security_manager.get_client_ip(request)

    # 生成验证码
    captcha_generator = CaptchaGenerator()
    _, answer, image_data = captcha_generator.generate()

    # 将答案存储到安全配置中（使用IP作为键）
    security_manager.set_security_config(db, f"captcha_answer_{client_ip}", str(answer))

    return {
        "image_data": image_data
    }

@router.post("/send-mfa-code")
async def send_mfa_code(request: Request, db: Session = Depends(get_db)):
    """发送多因素认证码"""
    client_ip = security_manager.get_client_ip(request)

    # 检查是否启用MFA
    if not security_manager.is_mfa_enabled(db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="多因素认证未启用",
        )

    # 检查发送频率限制
    if not security_manager.can_send_mfa_code(db, client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="发送过于频繁，请1分钟后再试",
        )

    # 获取MFA通知类型
    notification_type = security_manager.get_mfa_notification_type(db)
    if not notification_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未配置多因素认证通知方式",
        )

    # 获取通知配置
    notification_config = db.query(NotificationConfig).filter(
        NotificationConfig.name == notification_type,
        NotificationConfig.is_active == True
    ).first()

    if not notification_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="通知配置不存在或未激活",
        )

    # 生成验证码
    code = security_manager.create_mfa_code(db, client_ip)

    # 发送通知
    notification_service = NotificationService()
    title = "Pinchy 登录验证码"
    content = f"您的登录验证码是：{code}，有效期5分钟。"

    success = await notification_service.send_notification(notification_config, title, content)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="验证码发送失败",
        )

    return {"message": "验证码已发送"}

@router.get("/security-status")
async def get_security_status(request: Request, db: Session = Depends(get_db)):
    """获取安全状态（登录前可访问，仅返回基本安全配置）"""
    client_ip = security_manager.get_client_ip(request)

    # 只返回登录页面需要的基本安全状态，不暴露敏感信息
    return {
        "captcha_enabled": security_manager.is_captcha_enabled(db),
        "mfa_enabled": security_manager.is_mfa_enabled(db),
        "show_captcha": security_manager.is_captcha_enabled(db) and
                       security_manager.get_failed_attempts_count(db, client_ip, "admin") >= 5
    }

@router.get("/security-status-detailed")
async def get_detailed_security_status(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取详细安全状态（需要认证）"""
    client_ip = security_manager.get_client_ip(request)

    # 检查是否需要显示验证码（失败次数>=5次且启用了验证码）
    failed_attempts = security_manager.get_failed_attempts_count(db, client_ip, current_user.username)
    is_ip_locked = security_manager.is_ip_locked(db, client_ip, current_user.username)
    lockout_remaining_minutes = security_manager.get_lockout_remaining_time(db, client_ip, current_user.username)

    # 如果启用了验证码且失败次数>=5次，或者IP被锁定但启用了验证码，都需要显示验证码
    show_captcha = security_manager.is_captcha_enabled(db) and (failed_attempts >= 5 or is_ip_locked)

    return {
        "captcha_enabled": security_manager.is_captcha_enabled(db),
        "ip_blocking_enabled": security_manager.is_ip_blocking_enabled(db),
        "mfa_enabled": security_manager.is_mfa_enabled(db),
        "show_captcha": show_captcha,  # 是否显示验证码
        "is_ip_locked": is_ip_locked,
        "failed_attempts": failed_attempts,
        "lockout_remaining_minutes": lockout_remaining_minutes,  # 剩余锁定时间（分钟）
        "lockout_duration_minutes": security_manager.lockout_duration  # 总锁定时间（分钟）
    }
