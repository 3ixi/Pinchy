#!/usr/bin/env python3
"""
数据库迁移脚本：添加任务分组和自动创建任务功能
仅限从1.25.1、1.25.2、1.25.3升级到1.25.5的老用户使用
首次使用1.25.5版本的用户不需要运行
Docker用户不需要运行，直接拉取最新镜像重新添加脚本和任务
"""
import sqlite3
import os
import sys

def migrate_database():
    """执行数据库迁移"""
    db_path = "pinchy.db"
    
    if not os.path.exists(db_path):
        print("数据库文件不存在，跳过迁移")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("开始数据库迁移...")
        
        # 检查tasks表是否已有group_name字段
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'group_name' not in columns:
            print("为tasks表添加group_name字段...")
            cursor.execute("ALTER TABLE tasks ADD COLUMN group_name VARCHAR(50) NOT NULL DEFAULT '默认'")
            print("✓ tasks表group_name字段添加成功")
        else:
            print("✓ tasks表group_name字段已存在")
        
        # 检查script_subscriptions表是否已有auto_create_tasks字段
        cursor.execute("PRAGMA table_info(script_subscriptions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'auto_create_tasks' not in columns:
            print("为script_subscriptions表添加auto_create_tasks字段...")
            cursor.execute("ALTER TABLE script_subscriptions ADD COLUMN auto_create_tasks BOOLEAN DEFAULT 0")
            print("✓ script_subscriptions表auto_create_tasks字段添加成功")
        else:
            print("✓ script_subscriptions表auto_create_tasks字段已存在")
        
        # 提交更改
        conn.commit()
        print("数据库迁移完成！")
        
    except Exception as e:
        print(f"迁移失败: {str(e)}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
