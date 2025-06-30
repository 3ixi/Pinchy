"""
Pinchy 启动脚本
"""
import os
import secrets
import uvicorn
from app.main import app

def ensure_secret_key():
    """确保SECRET_KEY存在，如果不存在则生成一个"""
    if not os.getenv("SECRET_KEY"):
        # 生成一个安全的随机密钥
        secret_key = secrets.token_hex(32)  # 64字符的十六进制字符串
        os.environ["SECRET_KEY"] = secret_key
        print(f"🔑 已生成新的SECRET_KEY: {secret_key[:16]}...")
    else:
        print("🔑 使用现有的SECRET_KEY")

if __name__ == "__main__":
    print("正在启动 Pinchy 系统...")

    # 确保SECRET_KEY存在
    ensure_secret_key()

    print("访问地址: http://localhost:8000")
    print("默认用户名: admin")
    print("默认密码: admin")
    print("按 Ctrl+C 停止服务")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
