"""
WebSocket连接管理
"""
import json
from typing import List
from fastapi import WebSocket, WebSocketDisconnect

class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        
    async def connect(self, websocket: WebSocket):
        """接受WebSocket连接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"WebSocket连接已建立，当前连接数: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"WebSocket连接已断开，当前连接数: {len(self.active_connections)}")
        
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """发送个人消息"""
        try:
            await websocket.send_text(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            print(f"发送个人消息失败: {str(e)}")
            self.disconnect(websocket)
            
    async def broadcast(self, message: dict):
        """广播消息给所有连接"""
        if not self.active_connections:
            return
            
        message_text = json.dumps(message, ensure_ascii=False)
        disconnected_connections = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_text)
            except Exception as e:
                print(f"广播消息失败: {str(e)}")
                disconnected_connections.append(connection)
                
        # 清理断开的连接
        for connection in disconnected_connections:
            self.disconnect(connection)

# 全局WebSocket管理器实例
websocket_manager = WebSocketManager()
