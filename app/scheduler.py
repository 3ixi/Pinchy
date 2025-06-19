"""
任务调度器
"""
import os
import asyncio
from datetime import datetime
from typing import Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.database import SessionLocal
from app.models import Task, TaskLog, EnvironmentVariable, ApiDebugConfig, ApiDebugLog, NotificationConfig, ScriptSubscription, SystemConfig
from app.websocket_manager import websocket_manager
from app.notification_service import notification_service

class TaskScheduler:
    """任务调度器类"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.running_tasks: Dict[int, Any] = {}
        # 任务日志缓存，用于存储正在运行任务的实时日志
        self.task_log_cache: Dict[int, Dict] = {}

    def get_command_config(self, db, command_type: str) -> str:
        """从数据库获取命令配置"""
        try:
            config_key = f"{command_type}_command"
            config = db.query(SystemConfig).filter(SystemConfig.config_key == config_key).first()
            if config:
                return str(config.config_value)
            else:
                # 返回默认命令
                return "python" if command_type == "python" else "node"
        except Exception as e:
            print(f"获取{command_type}命令配置失败: {str(e)}")
            # 返回默认命令
            return "python" if command_type == "python" else "node"

    def get_task_log_cache(self, task_id: int) -> Dict:
        """获取任务日志缓存"""
        return self.task_log_cache.get(task_id, {})

    def clear_task_log_cache(self, task_id: int):
        """清理任务日志缓存"""
        if task_id in self.task_log_cache:
            del self.task_log_cache[task_id]
        
    def start(self):
        """启动调度器"""
        self.scheduler.start()
        print("任务调度器已启动")
        
    def shutdown(self):
        """关闭调度器"""
        self.scheduler.shutdown()
        print("任务调度器已关闭")
        
    def load_tasks_from_db(self):
        """从数据库加载任务"""
        db = SessionLocal()
        try:
            # 加载普通任务
            tasks = db.query(Task).filter(Task.is_active == True).all()
            for task in tasks:
                self.add_task(task)
            print(f"已加载 {len(tasks)} 个活跃任务")

            # 加载接口调试配置
            debug_configs = db.query(ApiDebugConfig).filter(
                ApiDebugConfig.is_active == True,
                ApiDebugConfig.cron_expression.isnot(None),
                ApiDebugConfig.cron_expression != ''
            ).all()
            for config in debug_configs:
                self.add_debug_config(config)
            print(f"已加载 {len(debug_configs)} 个活跃接口调试配置")

            # 加载脚本订阅
            subscriptions = db.query(ScriptSubscription).filter(ScriptSubscription.is_active == True).all()
            for subscription in subscriptions:
                self.add_subscription(subscription)
            print(f"已加载 {len(subscriptions)} 个活跃脚本订阅")
        finally:
            db.close()
            
    def add_task(self, task: Task):
        """添加任务到调度器"""
        try:
            # 解析cron表达式
            cron_parts = task.cron_expression.split()
            if len(cron_parts) != 5:
                print(f"任务 {task.name} 的cron表达式格式错误: {task.cron_expression}")
                return
                
            minute, hour, day, month, day_of_week = cron_parts
            
            # 创建cron触发器
            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week
            )
            
            # 添加任务到调度器
            self.scheduler.add_job(
                func=self.execute_task,
                trigger=trigger,
                args=[task.id],
                id=str(task.id),
                name=task.name,
                replace_existing=True
            )
            print(f"已添加任务: {task.name}")
            
        except Exception as e:
            print(f"添加任务失败 {task.name}: {str(e)}")

    def add_debug_config(self, config: ApiDebugConfig):
        """添加接口调试配置到调度器"""
        try:
            # 解析cron表达式
            cron_parts = config.cron_expression.split()
            if len(cron_parts) != 5:
                print(f"接口调试配置 {config.name} 的cron表达式格式错误: {config.cron_expression}")
                return

            minute, hour, day, month, day_of_week = cron_parts

            # 创建cron触发器
            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week
            )

            # 添加任务到调度器
            self.scheduler.add_job(
                func=self.execute_debug_config,
                trigger=trigger,
                args=[config.id],
                id=f"debug_{config.id}",
                name=f"接口调试_{config.name}",
                replace_existing=True
            )
            print(f"已添加接口调试配置: {config.name}")

        except Exception as e:
            print(f"添加接口调试配置失败 {config.name}: {str(e)}")

    def add_subscription(self, subscription: ScriptSubscription):
        """添加脚本订阅到调度器"""
        try:
            # 解析cron表达式
            cron_parts = subscription.cron_expression.split()
            if len(cron_parts) != 5:
                print(f"脚本订阅 {subscription.name} 的cron表达式格式错误: {subscription.cron_expression}")
                return

            minute, hour, day, month, day_of_week = cron_parts

            # 创建cron触发器
            trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week
            )

            # 添加任务到调度器
            self.scheduler.add_job(
                func=self.execute_subscription,
                trigger=trigger,
                args=[subscription.id],
                id=f"subscription_{subscription.id}",
                name=f"脚本订阅_{subscription.name}",
                replace_existing=True
            )
            print(f"已添加脚本订阅: {subscription.name}")

        except Exception as e:
            print(f"添加脚本订阅失败 {subscription.name}: {str(e)}")

    def remove_task(self, task_id: int):
        """从调度器移除任务"""
        try:
            self.scheduler.remove_job(str(task_id))
            print(f"已移除任务: {task_id}")
        except Exception as e:
            print(f"移除任务失败 {task_id}: {str(e)}")

    def remove_debug_config(self, config_id: int):
        """从调度器移除接口调试配置"""
        try:
            self.scheduler.remove_job(f"debug_{config_id}")
            print(f"已移除接口调试配置: {config_id}")
        except Exception as e:
            print(f"移除接口调试配置失败 {config_id}: {str(e)}")

    def remove_subscription(self, subscription_id: int):
        """从调度器移除脚本订阅"""
        try:
            self.scheduler.remove_job(f"subscription_{subscription_id}")
            print(f"已移除脚本订阅: {subscription_id}")
        except Exception as e:
            print(f"移除脚本订阅失败 {subscription_id}: {str(e)}")

    def run_task_immediately(self, task_id: int):
        """立即运行任务"""
        try:
            # 创建一个立即执行的任务
            self.scheduler.add_job(
                func=self.execute_task,
                args=[task_id],
                id=f"immediate_{task_id}_{datetime.now().timestamp()}",
                name=f"立即执行任务_{task_id}",
                replace_existing=False
            )
            print(f"已提交立即执行任务: {task_id}")
        except Exception as e:
            print(f"立即执行任务失败 {task_id}: {str(e)}")
            raise e
            
    async def execute_task(self, task_id: int):
        """执行任务"""
        db = SessionLocal()
        try:
            # 获取任务信息
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                print(f"任务不存在: {task_id}")
                return
                
            # 创建任务日志
            task_log = TaskLog(
                task_id=task.id,
                task_name=task.name,
                status="running",
                start_time=datetime.now()
            )
            db.add(task_log)
            db.commit()

            # 初始化任务日志缓存
            self.task_log_cache[task_id] = {
                "log_id": task_log.id,
                "output_lines": [],
                "error_lines": [],
                "start_time": datetime.now()
            }

            # 发送WebSocket消息到全局房间
            await websocket_manager.broadcast({
                "type": "task_start",
                "task_id": task.id,
                "task_name": task.name,
                "log_id": task_log.id
            }, "global")
            
            # 准备环境变量
            env_vars = os.environ.copy()

            # 设置UTF-8编码相关环境变量
            env_vars['PYTHONIOENCODING'] = 'utf-8'
            env_vars['LANG'] = 'zh_CN.UTF-8'
            env_vars['LC_ALL'] = 'zh_CN.UTF-8'

            # 设置Node.js相关环境变量（特别是在Docker环境下）
            script_type = str(task.script_type)
            if script_type == "nodejs":
                # 确保Node.js能找到全局模块
                if 'NODE_PATH' not in env_vars:
                    # 尝试获取npm全局路径
                    try:
                        import subprocess
                        import platform
                        is_windows = platform.system().lower() == 'windows'

                        result = subprocess.run(
                            ["npm", "root", "-g"],
                            capture_output=True,
                            text=True,
                            timeout=10,
                            shell=is_windows
                        )
                        if result.returncode == 0 and result.stdout.strip():
                            env_vars['NODE_PATH'] = result.stdout.strip()
                            print(f"✓ 设置NODE_PATH: {result.stdout.strip()}")
                        else:
                            # 使用默认路径
                            default_node_path = "/usr/local/lib/node_modules"
                            env_vars['NODE_PATH'] = default_node_path
                            print(f"✓ 使用默认NODE_PATH: {default_node_path}")
                    except Exception as e:
                        print(f"⚠️ 获取NODE_PATH失败: {e}")
                        # 使用默认路径
                        default_node_path = "/usr/local/lib/node_modules"
                        env_vars['NODE_PATH'] = default_node_path
                        print(f"✓ 使用默认NODE_PATH: {default_node_path}")

            # 添加数据库中的环境变量
            db_env_vars = db.query(EnvironmentVariable).all()
            for env_var in db_env_vars:
                env_vars[str(env_var.key)] = str(env_var.value)

            # 添加任务特定的环境变量
            if task.environment_vars is not None:
                for key, value in task.environment_vars.items():
                    env_vars[str(key)] = str(value)
            
            # 执行脚本
            try:
                # 确定脚本的完整路径
                scripts_dir = os.path.join(os.getcwd(), "scripts")
                script_full_path = os.path.join(scripts_dir, str(task.script_path))

                # 确保scripts目录存在
                os.makedirs(scripts_dir, exist_ok=True)

                # 检查脚本文件是否存在
                if not os.path.exists(script_full_path):
                    raise FileNotFoundError(f"脚本文件不存在: {script_full_path}")

                if script_type == "python":
                    python_command = self.get_command_config(db, "python")
                    cmd = [python_command, script_full_path]
                    # Python脚本在当前工作目录执行
                    cwd = os.getcwd()
                elif script_type == "nodejs":
                    nodejs_command = self.get_command_config(db, "nodejs")
                    cmd = [nodejs_command, script_full_path]
                    # Node.js脚本在scripts目录下执行，这样可以更好地处理相对路径的依赖
                    cwd = scripts_dir
                    print(f"✓ Node.js脚本将在目录 {cwd} 下执行")
                    print(f"✓ NODE_PATH: {env_vars.get('NODE_PATH', '未设置')}")
                else:
                    raise ValueError(f"不支持的脚本类型: {script_type}")

                print(f"执行命令: {' '.join(cmd)}")

                # 执行命令，工作目录设置为scripts目录
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env_vars,
                    cwd=scripts_dir
                )
                
                self.running_tasks[task_id] = {"process": process, "log_id": task_log.id}
                
                # 使用 pty 模块来获取真正的流式输出（仅Unix/Linux）
                import subprocess
                import threading
                import queue

                # 存储输出
                output_lines = []
                error_lines = []
                output_queue = queue.Queue()

                def read_output(pipe, output_list, output_type):
                    """读取输出的线程函数"""
                    try:
                        for line in iter(pipe.readline, b''):
                            if line:
                                line_text = line.decode('utf-8', errors='ignore')
                                output_list.append(line_text)
                                line_stripped = line_text.rstrip()
                                output_queue.put((output_type, line_stripped))

                                # 缓存日志行
                                if task_id in self.task_log_cache:
                                    if output_type == 'stdout':
                                        self.task_log_cache[task_id]["output_lines"].append(line_stripped)
                                    else:
                                        self.task_log_cache[task_id]["error_lines"].append(line_stripped)
                    except Exception as e:
                        print(f"读取输出时出错: {e}")
                    finally:
                        pipe.close()

                # 设置环境变量强制无缓冲输出
                env_vars['PYTHONUNBUFFERED'] = '1'
                env_vars['PYTHONIOENCODING'] = 'utf-8'

                # 确定工作目录
                if script_type == "nodejs":
                    # Node.js脚本在scripts目录下执行，便于处理相对路径依赖
                    work_dir = scripts_dir
                else:
                    # Python脚本在应用根目录执行
                    work_dir = os.getcwd()

                # 启动进程
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env_vars,
                    cwd=work_dir,
                    bufsize=0,  # 无缓冲
                    universal_newlines=False  # 使用字节模式
                )

                # 启动读取线程
                stdout_thread = threading.Thread(
                    target=read_output,
                    args=(process.stdout, output_lines, 'stdout')
                )
                stderr_thread = threading.Thread(
                    target=read_output,
                    args=(process.stderr, error_lines, 'stderr')
                )

                stdout_thread.start()
                stderr_thread.start()

                # 实时处理输出
                async def process_output():
                    while process.poll() is None or not output_queue.empty():
                        try:
                            # 非阻塞获取输出
                            output_type, line = output_queue.get_nowait()

                            # 通过WebSocket实时发送到任务特定房间
                            await websocket_manager.broadcast({
                                "type": "task_output",
                                "task_id": task.id,
                                "log_id": task_log.id,
                                "output_line": line,
                                "output_type": output_type
                            }, f"task_{task.id}")

                        except queue.Empty:
                            await asyncio.sleep(0.1)
                        except Exception as e:
                            print(f"处理输出时出错: {e}")
                            break

                # 启动输出处理
                await process_output()

                # 等待线程完成
                stdout_thread.join()
                stderr_thread.join()

                # 等待进程完成
                process.wait()

                # 更新最终状态
                db.query(TaskLog).filter(TaskLog.id == task_log.id).update({
                    "end_time": datetime.now(),
                    "exit_code": process.returncode,
                    "output": ''.join(output_lines),
                    "error_output": ''.join(error_lines),
                    "status": "success" if process.returncode == 0 else "failed"
                })
                db.commit()

                # 重新获取更新后的任务日志
                db.refresh(task_log)

                # 发送WebSocket消息到全局房间
                await websocket_manager.broadcast({
                    "type": "task_complete",
                    "task_id": task.id,
                    "task_name": task.name,
                    "log_id": task_log.id,
                    "status": task_log.status,
                    "exit_code": process.returncode,
                    "output": task_log.output,
                    "error_output": task_log.error_output
                }, "global")

                # 发送任务完成通知
                try:
                    await notification_service.send_task_notification(task.id, task_log)
                except Exception as e:
                    print(f"发送任务通知失败: {e}")
                
            except Exception as e:
                # 执行出错
                db.query(TaskLog).filter(TaskLog.id == task_log.id).update({
                    "end_time": datetime.now(),
                    "status": "failed",
                    "error_output": str(e)
                })
                db.commit()

                # 重新获取更新后的任务日志
                db.refresh(task_log)

                # 发送WebSocket消息到全局房间
                await websocket_manager.broadcast({
                    "type": "task_error",
                    "task_id": task.id,
                    "task_name": task.name,
                    "log_id": task_log.id,
                    "error": str(e)
                }, "global")

                # 发送任务失败通知
                try:
                    await notification_service.send_task_notification(task.id, task_log)
                except Exception as e:
                    print(f"发送任务通知失败: {e}")
                
            finally:
                # 清理运行中的任务记录
                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]

                # 延迟清理日志缓存，给WebSocket连接时间获取历史日志
                async def delayed_cache_cleanup():
                    await asyncio.sleep(300)  # 5分钟后清理缓存
                    self.clear_task_log_cache(task_id)

                # 启动延迟清理任务
                asyncio.create_task(delayed_cache_cleanup())
                    
        except Exception as e:
            print(f"执行任务时发生错误 {task_id}: {str(e)}")
        finally:
            db.close()

    async def stop_task(self, task_id: int, force: bool = False) -> bool:
        """停止正在运行的任务"""
        if task_id not in self.running_tasks:
            return False

        try:
            import signal
            import psutil

            # 获取任务进程信息
            task_info = self.running_tasks[task_id]
            if 'process' in task_info:
                process = task_info['process']

                if not force:
                    # 优雅停止：发送SIGTERM信号
                    try:
                        if hasattr(process, 'pid'):
                            parent = psutil.Process(process.pid)
                            # 终止所有子进程
                            for child in parent.children(recursive=True):
                                child.terminate()
                            parent.terminate()

                            # 等待进程结束
                            try:
                                parent.wait(timeout=5)
                            except psutil.TimeoutExpired:
                                # 如果5秒后还没结束，强制杀死
                                for child in parent.children(recursive=True):
                                    child.kill()
                                parent.kill()
                        else:
                            process.terminate()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                else:
                    # 强制停止：发送SIGKILL信号
                    try:
                        if hasattr(process, 'pid'):
                            parent = psutil.Process(process.pid)
                            for child in parent.children(recursive=True):
                                child.kill()
                            parent.kill()
                        else:
                            process.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                # 更新数据库中的任务日志状态
                db = SessionLocal()
                try:
                    task_log = db.query(TaskLog).filter(
                        TaskLog.task_id == task_id,
                        TaskLog.status == "running"
                    ).order_by(TaskLog.start_time.desc()).first()

                    if task_log:
                        from datetime import datetime
                        db.query(TaskLog).filter(TaskLog.id == task_log.id).update({
                            "end_time": datetime.now(),
                            "status": "stopped",
                            "error_output": "任务被用户停止"
                        })
                        db.commit()

                        # 发送WebSocket消息
                        await websocket_manager.broadcast({
                            "type": "task_complete",
                            "task_id": task_id,
                            "task_name": task_log.task_name,
                            "log_id": task_log.id,
                            "status": "stopped",
                            "exit_code": -1,
                            "output": task_log.output,
                            "error_output": task_log.error_output
                        }, "global")

                        # 发送任务停止通知
                        try:
                            await notification_service.send_task_notification(task_id, task_log)
                        except Exception as e:
                            print(f"发送任务通知失败: {e}")

                finally:
                    db.close()

                # 清理运行中的任务记录
                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]

                # 延迟清理日志缓存
                async def delayed_cache_cleanup():
                    await asyncio.sleep(300)  # 5分钟后清理缓存
                    self.clear_task_log_cache(task_id)

                # 启动延迟清理任务
                asyncio.create_task(delayed_cache_cleanup())

                return True

        except Exception as e:
            print(f"停止任务 {task_id} 时发生错误: {str(e)}")
            return False

        return False

    async def execute_debug_config(self, config_id: int):
        """执行接口调试配置"""
        import requests
        import time
        import re

        db = SessionLocal()
        try:
            # 获取配置信息
            config = db.query(ApiDebugConfig).filter(ApiDebugConfig.id == config_id).first()
            if not config:
                print(f"接口调试配置不存在: {config_id}")
                return

            start_time = datetime.now()

            # 获取环境变量
            env_vars = {}
            env_records = db.query(EnvironmentVariable).all()
            for env_record in env_records:
                env_vars[env_record.key] = env_record.value

            # 变量替换函数
            def replace_variables(text: str) -> str:
                if not text:
                    return text

                # 生成统一的时间戳
                timestamp_10 = str(int(time.time()))
                timestamp_13 = str(int(time.time() * 1000))

                # 替换时间戳变量
                text = re.sub(r'\[timestmp\.10\]', timestamp_10, text)
                text = re.sub(r'\[timestmp\.13\]', timestamp_13, text)
                text = re.sub(r'\[timestmp\]', timestamp_13, text)  # 默认13位

                # 替换随机数变量
                def replace_random_var(match):
                    range_str = match.group(1)
                    try:
                        # 解析范围，支持格式：100-500
                        if '-' in range_str:
                            min_val, max_val = range_str.split('-', 1)
                            min_val = int(min_val.strip())
                            max_val = int(max_val.strip())
                            if min_val <= max_val:
                                import random
                                return str(random.randint(min_val, max_val))
                        # 如果格式不正确，保持原样
                        return f'[random.{range_str}]'
                    except (ValueError, TypeError):
                        # 如果解析失败，保持原样
                        return f'[random.{range_str}]'

                text = re.sub(r'\[random\.([^]]+)\]', replace_random_var, text)

                # 替换环境变量
                def replace_env_var(match):
                    var_name = match.group(1)
                    return env_vars.get(var_name, f'[getenv.{var_name}]')

                text = re.sub(r'\[getenv\.([^]]+)\]', replace_env_var, text)
                return text

            # 替换变量
            url = replace_variables(config.url)

            # 先替换payload中的变量，因为Content-Length需要基于替换后的payload计算
            payload = replace_variables(config.payload) if config.payload else None

            # 处理headers，特别注意Content-Length的处理
            headers = {}
            auto_calculate_content_length = False

            for key, value in (config.headers or {}).items():
                # 检查是否需要自动计算Content-Length
                if key.lower() == 'content-length' and value == '自动计算':
                    auto_calculate_content_length = True
                    continue
                headers[replace_variables(key)] = replace_variables(value)

            # 自动设置Host头
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(url)
                if parsed_url.netloc:
                    headers['Host'] = parsed_url.netloc
            except:
                pass

            # 自动设置Content-Length（基于替换变量后的payload）
            if payload and config.method.upper() in ['POST', 'PUT', 'PATCH']:
                if auto_calculate_content_length or 'Content-Length' not in headers:
                    headers['Content-Length'] = str(len(payload.encode('utf-8')))

            # 自动设置Content-Length（只有在有payload时才设置）
            if payload and config.method.upper() in ['POST', 'PUT', 'PATCH']:
                headers['Content-Length'] = str(len(payload.encode('utf-8')))

            try:
                # 发送请求，确保正确处理UTF-8编码
                if payload:
                    # 将payload编码为UTF-8字节
                    payload_bytes = payload.encode('utf-8')
                    response = requests.request(
                        method=config.method.upper(),
                        url=url,
                        headers=headers,
                        data=payload_bytes,
                        timeout=30
                    )
                else:
                    response = requests.request(
                        method=config.method.upper(),
                        url=url,
                        headers=headers,
                        timeout=30
                    )

                end_time = datetime.now()
                response_time = int((end_time - start_time).total_seconds() * 1000)

                # 创建执行日志
                debug_log = ApiDebugLog(
                    config_id=config.id,
                    config_name=config.name,
                    method=config.method,
                    url=url,
                    request_headers=headers,
                    request_payload=payload,
                    response_status=response.status_code,
                    response_headers=dict(response.headers),
                    response_body=response.text,
                    response_time=response_time,
                    status="success",
                    start_time=start_time,
                    end_time=end_time
                )
                db.add(debug_log)
                db.commit()

                print(f"接口调试配置 {config.name} 执行成功，状态码: {response.status_code}")

                # 发送通知
                if config.notification_enabled:
                    print(f"接口调试配置 {config.name} 启用了通知，类型: '{config.notification_type}'")

                    if not config.notification_type or config.notification_type.strip() == '':
                        print(f"警告: 接口调试配置 {config.name} 启用了通知但未设置通知类型")
                        return

                    should_notify = (
                        config.notification_condition == "always" or
                        (config.notification_condition == "success" and response.status_code < 400) or
                        (config.notification_condition == "error" and response.status_code >= 400)
                    )
                    print(f"通知条件: {config.notification_condition}, 状态码: {response.status_code}, 是否发送: {should_notify}")

                    if should_notify:
                        try:
                            notification_config = db.query(NotificationConfig).filter(
                                NotificationConfig.name == config.notification_type,
                                NotificationConfig.is_active == True
                            ).first()

                            print(f"查找通知配置: name='{config.notification_type}', 找到: {notification_config is not None}")
                            if notification_config:
                                print(f"通知配置详情: id={notification_config.id}, name={notification_config.name}, is_active={notification_config.is_active}")

                            if notification_config:
                                message = f"接口调试定时执行结果\n"
                                message += f"配置名称: {config.name}\n"
                                message += f"URL: {url}\n"
                                message += f"方法: {config.method.upper()}\n"
                                message += f"状态码: {response.status_code}\n"
                                message += f"响应时间: {response_time}ms\n"
                                # 增加响应内容长度，最多显示1000字符
                                response_content = response.text[:1000]
                                if len(response.text) > 1000:
                                    response_content += "...(内容过长已截断)"
                                message += f"响应内容: {response_content}"

                                # 使用通知服务发送通知
                                result = await notification_service.send_notification(notification_config, "接口调试定时执行通知", message)
                                print(f"通知发送结果: {result}")
                            else:
                                print(f"未找到激活的通知配置: '{config.notification_type}'")
                                # 列出所有可用的通知配置
                                all_configs = db.query(NotificationConfig).filter(NotificationConfig.is_active == True).all()
                                print(f"可用的通知配置: {[c.name for c in all_configs]}")
                        except Exception as e:
                            print(f"发送通知失败: {str(e)}")

            except Exception as e:
                end_time = datetime.now()
                response_time = int((end_time - start_time).total_seconds() * 1000)

                # 创建错误日志
                debug_log = ApiDebugLog(
                    config_id=config.id,
                    config_name=config.name,
                    method=config.method,
                    url=url,
                    request_headers=headers,
                    request_payload=payload,
                    response_time=response_time,
                    error_message=str(e),
                    status="error",
                    start_time=start_time,
                    end_time=end_time
                )
                db.add(debug_log)
                db.commit()

                print(f"接口调试配置 {config.name} 执行失败: {str(e)}")

                # 发送错误通知
                if config.notification_enabled and config.notification_type and config.notification_condition in ["always", "error"]:
                    try:
                        notification_config = db.query(NotificationConfig).filter(
                            NotificationConfig.name == config.notification_type,
                            NotificationConfig.is_active == True
                        ).first()

                        if notification_config:
                            message = f"接口调试定时执行失败\n"
                            message += f"配置名称: {config.name}\n"
                            message += f"URL: {url}\n"
                            message += f"方法: {config.method.upper()}\n"
                            message += f"错误信息: {str(e)}\n"
                            message += f"响应时间: {response_time}ms"

                            # 使用通知服务发送通知
                            await notification_service.send_notification(notification_config, "接口调试定时执行错误通知", message)
                    except Exception as e:
                        print(f"发送通知失败: {str(e)}")

        except Exception as e:
            print(f"执行接口调试配置时发生错误 {config_id}: {str(e)}")
        finally:
            db.close()

    async def execute_subscription(self, subscription_id: int):
        """执行脚本订阅同步"""
        # 导入放在这里避免循环导入
        from app.routers.subscriptions import execute_subscription_sync

        try:
            await execute_subscription_sync(subscription_id)
        except Exception as e:
            print(f"执行脚本订阅失败 {subscription_id}: {str(e)}")

    def stop(self):
        """停止调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            print("任务调度器已停止")

# 全局调度器实例
task_scheduler = TaskScheduler()
