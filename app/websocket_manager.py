"""
WebSocket连接管理器
"""
from typing import Dict, List
from fastapi import WebSocket
import json
import asyncio


class WebSocketManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        # 存储活跃连接 {room_id: [websocket1, websocket2, ...]}
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, room_id: str):
        """接受WebSocket连接"""
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
        self.active_connections[room_id].append(websocket)
        print(f"WebSocket连接已建立: {room_id}, 当前连接数: {len(self.active_connections[room_id])}")
    
    def disconnect(self, websocket: WebSocket, room_id: str):
        """断开WebSocket连接"""
        if room_id in self.active_connections:
            if websocket in self.active_connections[room_id]:
                self.active_connections[room_id].remove(websocket)
                print(f"WebSocket连接已断开: {room_id}, 当前连接数: {len(self.active_connections[room_id])}")
            
            # 如果房间没有连接了，删除房间
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """发送个人消息"""
        try:
            await websocket.send_text(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            print(f"发送个人消息失败: {e}")
    
    async def broadcast(self, message: dict, room_id: str = None):
        """广播消息到指定房间或所有连接"""
        message_text = json.dumps(message, ensure_ascii=False)
        
        if room_id:
            # 发送到指定房间
            if room_id in self.active_connections:
                disconnected = []
                for connection in self.active_connections[room_id]:
                    try:
                        await connection.send_text(message_text)
                    except Exception as e:
                        print(f"发送消息到 {room_id} 失败: {e}")
                        disconnected.append(connection)
                
                # 清理断开的连接
                for connection in disconnected:
                    self.disconnect(connection, room_id)
        else:
            # 广播到所有房间
            for room_id, connections in self.active_connections.items():
                disconnected = []
                for connection in connections:
                    try:
                        await connection.send_text(message_text)
                    except Exception as e:
                        print(f"广播消息到 {room_id} 失败: {e}")
                        disconnected.append(connection)
                
                # 清理断开的连接
                for connection in disconnected:
                    self.disconnect(connection, room_id)
    
    def get_connection_count(self, room_id: str = None) -> int:
        """获取连接数"""
        if room_id:
            return len(self.active_connections.get(room_id, []))
        else:
            return sum(len(connections) for connections in self.active_connections.values())


# 全局WebSocket管理器实例
websocket_manager = WebSocketManager()
