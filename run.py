"""
Pinchy 启动脚本
"""
import uvicorn
from app.main import app

if __name__ == "__main__":
    print("正在启动 Pinchy 系统...")
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
