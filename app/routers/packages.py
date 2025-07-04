"""
包管理相关路由
"""
import subprocess
import json
import asyncio
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.auth import get_current_user
from app.models import User, PackageInfo, SystemConfig
from app.websocket_manager import websocket_manager

router = APIRouter(prefix="/api/packages", tags=["包管理"])

class PackageInstall(BaseModel):
    package_type: str  # python 或 nodejs
    package_name: str
    version: Optional[str] = None

class PackageResponse(BaseModel):
    id: int
    package_type: str
    package_name: str
    version: Optional[str]
    installed_at: str

    class Config:
        from_attributes = True

class InstalledPackage(BaseModel):
    name: str
    version: str

def get_package_manager_config(db: Session, package_type: str) -> str:
    """从数据库获取包管理器配置"""
    try:
        config_key = f"{package_type}_package_manager"
        config = db.query(SystemConfig).filter(SystemConfig.config_key == config_key).first()
        if config:
            return str(config.config_value)
        else:
            # 返回默认包管理器
            return "pip" if package_type == "python" else "npm"
    except Exception as e:
        print(f"获取{package_type}包管理器配置失败: {str(e)}")
        # 返回默认包管理器
        return "pip" if package_type == "python" else "npm"

def get_package_manager_commands(manager: str, package_type: str, action: str, package_name: str, version: Optional[str] = None) -> List[str]:
    """根据包管理器类型生成命令"""
    if package_type == "python":
        if manager == "pip":
            if action == "install":
                cmd = ["pip", "install"]
                if version:
                    cmd.append(f"{package_name}=={version}")
                else:
                    cmd.append(package_name)
            elif action == "uninstall":
                cmd = ["pip", "uninstall", "-y", package_name]
            elif action == "list":
                cmd = ["pip", "list", "--format=json"]
            else:
                raise ValueError(f"不支持的操作: {action}")
        elif manager == "conda":
            if action == "install":
                cmd = ["conda", "install", "-y"]
                if version:
                    cmd.append(f"{package_name}={version}")
                else:
                    cmd.append(package_name)
            elif action == "uninstall":
                cmd = ["conda", "remove", "-y", package_name]
            elif action == "list":
                cmd = ["conda", "list", "--json"]
            else:
                raise ValueError(f"不支持的操作: {action}")
        elif manager == "poetry":
            if action == "install":
                if version:
                    cmd = ["poetry", "add", f"{package_name}=={version}"]
                else:
                    cmd = ["poetry", "add", package_name]
            elif action == "uninstall":
                cmd = ["poetry", "remove", package_name]
            elif action == "list":
                cmd = ["poetry", "show", "--no-dev"]
            else:
                raise ValueError(f"不支持的操作: {action}")
        else:
            raise ValueError(f"不支持的Python包管理器: {manager}")
    elif package_type == "nodejs":
        if manager == "npm":
            if action == "install":
                cmd = ["npm", "install", "-g"]
                if version:
                    cmd.append(f"{package_name}@{version}")
                else:
                    cmd.append(package_name)
            elif action == "uninstall":
                cmd = ["npm", "uninstall", "-g", package_name]
            elif action == "list":
                cmd = ["npm", "list", "-g", "--json", "--depth=0"]
            else:
                raise ValueError(f"不支持的操作: {action}")
        elif manager == "yarn":
            if action == "install":
                cmd = ["yarn", "global", "add"]
                if version:
                    cmd.append(f"{package_name}@{version}")
                else:
                    cmd.append(package_name)
            elif action == "uninstall":
                cmd = ["yarn", "global", "remove", package_name]
            elif action == "list":
                cmd = ["yarn", "global", "list", "--json"]
            else:
                raise ValueError(f"不支持的操作: {action}")
        elif manager == "pnpm":
            if action == "install":
                cmd = ["pnpm", "add", "-g"]
                if version:
                    cmd.append(f"{package_name}@{version}")
                else:
                    cmd.append(package_name)
            elif action == "uninstall":
                cmd = ["pnpm", "remove", "-g", package_name]
            elif action == "list":
                cmd = ["pnpm", "list", "-g", "--json"]
            else:
                raise ValueError(f"不支持的操作: {action}")
        else:
            raise ValueError(f"不支持的Node.js包管理器: {manager}")
    else:
        raise ValueError(f"不支持的包类型: {package_type}")

    return cmd

async def run_command(cmd: List[str]) -> tuple[int, str, str]:
    """执行命令并返回结果"""
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return_code = process.returncode if process.returncode is not None else 1
        return return_code, stdout.decode('utf-8'), stderr.decode('utf-8')
    except Exception as e:
        return 1, "", str(e)

async def install_package_with_websocket(package_data: PackageInstall, db: Session):
    """异步安装包并通过WebSocket发送实时日志"""
    try:
        # 发送安装开始消息
        await websocket_manager.broadcast({
            "type": "package_install_start",
            "package_type": package_data.package_type,
            "package_name": package_data.package_name,
            "version": package_data.version
        }, "global")

        # 获取配置的包管理器
        package_manager = get_package_manager_config(db, package_data.package_type)

        # 生成安装命令
        cmd = get_package_manager_commands(
            package_manager,
            package_data.package_type,
            "install",
            package_data.package_name,
            package_data.version
        )

        # 创建子进程并实时读取输出
        import os
        import platform
        cwd = os.getcwd()  # 使用当前工作目录而不是固定的/scripts
        is_windows = platform.system().lower() == 'windows'

        # 在Windows上，某些包管理器需要shell=True
        if is_windows and package_data.package_type == "nodejs":
            # 对于Windows上的Node.js包管理器，使用shell模式
            cmd_str = ' '.join(cmd)
            process = await asyncio.create_subprocess_shell(
                cmd_str,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,  # 将stderr重定向到stdout
                cwd=cwd
            )
        else:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,  # 将stderr重定向到stdout
                cwd=cwd
            )

        # 发送命令信息到WebSocket
        cmd_display = cmd_str if is_windows and package_data.package_type == "nodejs" else ' '.join(cmd)
        await websocket_manager.broadcast({
            "type": "package_install_output",
            "output": f"执行命令: {cmd_display}"
        }, "global")

        # 实时读取输出
        while True:
            if process.stdout is None:
                break
            line = await process.stdout.readline()
            if not line:
                break

            output = line.decode('utf-8', errors='ignore').strip()
            if output:
                # 发送输出到WebSocket
                await websocket_manager.broadcast({
                    "type": "package_install_output",
                    "output": output
                }, "global")

        # 等待进程完成
        await process.wait()

        success = process.returncode == 0

        if success:
            # 保存到数据库
            package_info = PackageInfo(
                package_type=package_data.package_type,
                package_name=package_data.package_name,
                version=package_data.version
            )
            db.add(package_info)
            db.commit()

        # 发送完成消息
        await websocket_manager.broadcast({
            "type": "package_install_complete",
            "success": success,
            "package_type": package_data.package_type,
            "package_name": package_data.package_name
        }, "global")

    except Exception as e:
        # 发送错误消息
        await websocket_manager.broadcast({
            "type": "package_install_output",
            "output": f"安装过程中发生错误: {str(e)}"
        }, "global")

        await websocket_manager.broadcast({
            "type": "package_install_complete",
            "success": False,
            "package_type": package_data.package_type,
            "package_name": package_data.package_name
        }, "global")

async def uninstall_package_with_websocket(package_type: str, package_name: str, db: Session):
    """异步卸载包并通过WebSocket发送实时日志"""
    try:
        # 发送卸载开始消息
        await websocket_manager.broadcast({
            "type": "package_uninstall_start",
            "package_type": package_type,
            "package_name": package_name
        }, "global")

        # 获取配置的包管理器
        package_manager = get_package_manager_config(db, package_type)

        # 生成卸载命令
        cmd = get_package_manager_commands(
            package_manager,
            package_type,
            "uninstall",
            package_name
        )

        # 创建子进程并实时读取输出
        import os
        import platform
        cwd = os.getcwd()
        is_windows = platform.system().lower() == 'windows'

        # 在Windows上，某些包管理器需要shell=True
        if is_windows and package_type == "nodejs":
            # 对于Windows上的Node.js包管理器，使用shell模式
            cmd_str = ' '.join(cmd)
            process = await asyncio.create_subprocess_shell(
                cmd_str,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,  # 将stderr重定向到stdout
                cwd=cwd
            )
        else:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,  # 将stderr重定向到stdout
                cwd=cwd
            )

        # 实时读取输出
        while True:
            if process.stdout is None:
                break
            line = await process.stdout.readline()
            if not line:
                break

            output = line.decode('utf-8', errors='ignore').strip()
            if output:
                # 发送输出到WebSocket
                await websocket_manager.broadcast({
                    "type": "package_uninstall_output",
                    "output": output
                }, "global")

        # 等待进程完成
        await process.wait()

        success = process.returncode == 0

        if success:
            # 从数据库中删除记录
            package_info = db.query(PackageInfo).filter(
                PackageInfo.package_type == package_type,
                PackageInfo.package_name == package_name
            ).first()
            if package_info:
                db.delete(package_info)
                db.commit()

        # 发送完成消息
        await websocket_manager.broadcast({
            "type": "package_uninstall_complete",
            "success": success,
            "package_type": package_type,
            "package_name": package_name
        }, "global")

    except Exception as e:
        # 发送错误消息
        await websocket_manager.broadcast({
            "type": "package_uninstall_output",
            "output": f"卸载过程中发生错误: {str(e)}"
        }, "global")

        await websocket_manager.broadcast({
            "type": "package_uninstall_complete",
            "success": False,
            "package_type": package_type,
            "package_name": package_name
        }, "global")

@router.get("/python/list", response_model=List[InstalledPackage])
async def list_python_packages(current_user: User = Depends(get_current_user)):
    """列出已安装的Python包"""
    try:
        result = subprocess.run(
            ["pip", "list", "--format=json"],
            capture_output=True,
            text=True,
            check=True
        )
        packages_data = json.loads(result.stdout)
        return [
            InstalledPackage(name=pkg["name"], version=pkg["version"])
            for pkg in packages_data
        ]
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"获取Python包列表失败: {e.stderr}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="解析Python包列表失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取Python包列表失败: {str(e)}")

def detect_docker_environment():
    """检测是否在Docker环境中运行"""
    import os
    try:
        return (
            os.path.exists('/.dockerenv') or
            os.environ.get('DOCKER_CONTAINER') == 'true' or
            (os.path.exists('/proc/1/cgroup') and 'docker' in open('/proc/1/cgroup').read())
        )
    except Exception:
        return False

def get_npm_global_paths():
    """获取npm全局安装路径"""
    import subprocess
    import platform

    is_windows = platform.system().lower() == 'windows'
    is_docker = detect_docker_environment()

    paths = []

    try:
        # 获取npm全局路径
        result = subprocess.run(
            ["npm", "root", "-g"],
            capture_output=True,
            text=True,
            timeout=10,
            shell=is_windows
        )
        if result.returncode == 0 and result.stdout.strip():
            paths.append(result.stdout.strip())
    except Exception:
        pass

    try:
        # 获取npm配置的prefix路径
        result = subprocess.run(
            ["npm", "config", "get", "prefix"],
            capture_output=True,
            text=True,
            timeout=10,
            shell=is_windows
        )
        if result.returncode == 0 and result.stdout.strip():
            prefix_path = result.stdout.strip()
            if is_windows:
                paths.append(f"{prefix_path}\\node_modules")
            else:
                paths.append(f"{prefix_path}/lib/node_modules")
    except Exception:
        pass

    # Docker环境下的常见路径
    if is_docker:
        paths.extend([
            "/usr/local/lib/node_modules",
            "/usr/lib/node_modules",
            "/app/node_modules"
        ])

    return list(set(paths))  # 去重

@router.get("/nodejs/list", response_model=List[InstalledPackage])
async def list_nodejs_packages(current_user: User = Depends(get_current_user)):
    """列出已安装的Node.js包"""
    import platform
    import os
    is_windows = platform.system().lower() == 'windows'
    is_docker = detect_docker_environment()

    packages = []

    try:
        # 方法1: 使用 npm list -g --json --depth=0
        result = subprocess.run(
            ["npm", "list", "-g", "--json", "--depth=0"],
            capture_output=True,
            text=True,
            timeout=30,
            shell=is_windows
        )

        # npm list 命令即使成功也可能返回非0状态码（如果有警告）
        if result.stdout and result.stdout.strip():
            try:
                packages_data = json.loads(result.stdout)
                dependencies = packages_data.get("dependencies", {})
                packages.extend([
                    InstalledPackage(name=name, version=info.get("version", "unknown") if isinstance(info, dict) else str(info))
                    for name, info in dependencies.items()
                ])

                # 如果成功获取到包，记录调试信息
                if packages:
                    print(f"✓ 通过npm list获取到 {len(packages)} 个包")

            except json.JSONDecodeError as e:
                print(f"JSON解析失败: {e}")
                pass  # 如果JSON解析失败，继续尝试其他方法

        # 方法2: 如果JSON方法失败或没有获取到包，尝试使用简单的 npm list -g
        if not packages:
            print("尝试使用文本格式获取包列表...")
            try:
                result = subprocess.run(
                    ["npm", "list", "-g", "--depth=0"],
                    capture_output=True,
                    timeout=30,
                    shell=is_windows,
                    encoding='utf-8',
                    errors='ignore'  # 忽略编码错误
                )
            except Exception as e:
                print(f"文本格式命令执行失败: {e}")
                result = None

            if result and result.stdout:
                lines = result.stdout.split('\n')
                for line in lines:
                    line = line.strip()
                    # 处理格式如: +-- package-name@version 或 `-- package-name@version
                    if line and '@' in line:
                        # 移除前缀符号
                        if line.startswith(('+--', '`--', '├──', '└──')):
                            line = line[3:].strip()
                        elif line.startswith('│'):
                            continue  # 跳过树形结构的连接线

                        # 跳过npm自身和一些系统包（但保留用户安装的包）
                        if any(skip in line.lower() for skip in ['npm@', 'node@']):
                            continue

                        # 解析包名和版本
                        if '@' in line:
                            parts = line.split('@')
                            if len(parts) >= 2:
                                name = '@'.join(parts[:-1]) if parts[0] == '' else parts[0]
                                version = parts[-1]
                                # 清理包名中的特殊字符
                                name = name.strip(' ├└│─`+')
                                if name and version:
                                    packages.append(InstalledPackage(name=name, version=version))

                if packages:
                    print(f"✓ 通过文本解析获取到 {len(packages)} 个包")

        # 方法3: 在Docker环境下，直接扫描node_modules目录
        if is_docker and not packages:
            print("Docker环境下尝试直接扫描node_modules目录...")
            npm_paths = get_npm_global_paths()

            for npm_path in npm_paths:
                if os.path.exists(npm_path):
                    print(f"扫描路径: {npm_path}")
                    try:
                        for item in os.listdir(npm_path):
                            item_path = os.path.join(npm_path, item)
                            if os.path.isdir(item_path) and not item.startswith('.'):
                                # 跳过npm自身和一些系统包
                                if item in ['npm', 'node']:
                                    continue

                                # 尝试读取package.json获取版本信息
                                package_json_path = os.path.join(item_path, 'package.json')
                                version = "unknown"
                                if os.path.exists(package_json_path):
                                    try:
                                        with open(package_json_path, 'r', encoding='utf-8') as f:
                                            package_info = json.load(f)
                                            version = package_info.get('version', 'unknown')
                                    except Exception:
                                        pass

                                # 检查是否已经在列表中
                                if not any(pkg.name == item for pkg in packages):
                                    packages.append(InstalledPackage(name=item, version=version))
                    except Exception as e:
                        print(f"扫描目录 {npm_path} 失败: {e}")

            if packages:
                print(f"✓ 通过目录扫描获取到 {len(packages)} 个包")

        # 方法4: 尝试获取本地安装的包（如果存在package.json）
        try:
            if os.path.exists("package.json"):
                print("检测到package.json，尝试获取本地包...")
                result = subprocess.run(
                    ["npm", "list", "--json", "--depth=0"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    shell=is_windows
                )

                if result.stdout and result.stdout.strip():
                    try:
                        local_packages_data = json.loads(result.stdout)
                        local_dependencies = local_packages_data.get("dependencies", {})
                        local_count = 0
                        # 添加本地包，但标记为本地安装
                        for name, info in local_dependencies.items():
                            version = info.get("version", "unknown") if isinstance(info, dict) else str(info)
                            # 检查是否已经在全局包列表中
                            if not any(pkg.name == name for pkg in packages):
                                packages.append(InstalledPackage(name=f"{name} (本地)", version=version))
                                local_count += 1

                        if local_count > 0:
                            print(f"✓ 获取到 {local_count} 个本地包")
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass  # 忽略本地包获取错误

        # 输出最终结果
        print(f"最终获取到 {len(packages)} 个Node.js包")
        if packages:
            print("包列表:")
            for pkg in packages[:10]:  # 只显示前10个
                print(f"  - {pkg.name}@{pkg.version}")
            if len(packages) > 10:
                print(f"  ... 还有 {len(packages) - 10} 个包")

        return packages

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="获取Node.js包列表超时")
    except FileNotFoundError:
        # 返回空列表而不是抛出异常，这样前端可以正常显示
        return []
    except Exception as e:
        # 记录错误但返回空列表
        print(f"获取Node.js包列表时发生错误: {str(e)}")
        return []

@router.post("/install")
async def install_package(
    package_data: PackageInstall,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """安装包"""
    if package_data.package_type not in ["python", "nodejs"]:
        raise HTTPException(status_code=400, detail="包类型必须是 python 或 nodejs")

    # 检查环境
    import platform
    is_windows = platform.system().lower() == 'windows'

    if package_data.package_type == "python":
        try:
            # 检查Python环境
            result = subprocess.run(["python", "--version"], capture_output=True, text=True, timeout=10, shell=is_windows)
            if result.returncode != 0:
                # 尝试python3命令
                result = subprocess.run(["python3", "--version"], capture_output=True, text=True, timeout=10, shell=is_windows)
                if result.returncode != 0:
                    raise HTTPException(status_code=400, detail="Python环境未安装或不可用，无法安装Python包")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            raise HTTPException(status_code=400, detail="Python环境未安装或不可用，无法安装Python包")

    elif package_data.package_type == "nodejs":
        try:
            # 检查Node.js环境
            result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10, shell=is_windows)
            if result.returncode != 0:
                raise HTTPException(status_code=400, detail="Node.js环境未安装或不可用，无法安装Node.js包")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            raise HTTPException(status_code=400, detail="Node.js环境未安装或不可用，无法安装Node.js包")

    # 启动后台任务进行安装
    background_tasks.add_task(install_package_with_websocket, package_data, db)

    return {"message": "包安装已开始，请查看实时日志"}

@router.delete("/uninstall")
async def uninstall_package(
    package_type: str,
    package_name: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """卸载包"""
    if package_type not in ["python", "nodejs"]:
        raise HTTPException(status_code=400, detail="包类型必须是 python 或 nodejs")

    # 启动后台任务进行卸载
    background_tasks.add_task(uninstall_package_with_websocket, package_type, package_name, db)

    return {"message": "包卸载已开始，请查看实时日志"}

@router.get("/history", response_model=List[PackageResponse])
async def get_package_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取包安装历史"""
    packages = db.query(PackageInfo).all()
    return [
        PackageResponse(
            id=pkg.id,
            package_type=pkg.package_type,
            package_name=pkg.package_name,
            version=pkg.version,
            installed_at=pkg.installed_at.isoformat()
        )
        for pkg in packages
    ]

@router.get("/manager-config")
async def get_package_manager_config_api(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前包管理器配置"""
    try:
        python_manager = get_package_manager_config(db, "python")
        nodejs_manager = get_package_manager_config(db, "nodejs")

        return {
            "python_package_manager": python_manager,
            "nodejs_package_manager": nodejs_manager
        }
    except Exception as e:
        print(f"获取包管理器配置失败: {str(e)}")
        return {
            "python_package_manager": "pip",
            "nodejs_package_manager": "npm"
        }

@router.get("/debug/environment")
async def get_debug_environment_info(current_user: User = Depends(get_current_user)):
    """获取环境调试信息"""
    import platform
    import os

    try:
        is_docker = detect_docker_environment()
        is_windows = platform.system().lower() == 'windows'
        npm_paths = get_npm_global_paths()

        # 检查npm版本
        npm_version = "未知"
        try:
            result = subprocess.run(
                ["npm", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                shell=is_windows
            )
            if result.returncode == 0:
                npm_version = result.stdout.strip()
        except Exception:
            pass

        # 检查node版本
        node_version = "未知"
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                shell=is_windows
            )
            if result.returncode == 0:
                node_version = result.stdout.strip()
        except Exception:
            pass

        # 检查路径是否存在
        path_status = {}
        for path in npm_paths:
            path_status[path] = {
                "exists": os.path.exists(path),
                "is_dir": os.path.isdir(path) if os.path.exists(path) else False,
                "readable": os.access(path, os.R_OK) if os.path.exists(path) else False
            }

        return {
            "platform": platform.system(),
            "is_docker": is_docker,
            "is_windows": is_windows,
            "npm_version": npm_version,
            "node_version": node_version,
            "npm_paths": npm_paths,
            "path_status": path_status,
            "working_directory": os.getcwd(),
            "environment_variables": {
                "NODE_PATH": os.environ.get("NODE_PATH"),
                "NPM_CONFIG_PREFIX": os.environ.get("NPM_CONFIG_PREFIX"),
                "PATH": os.environ.get("PATH", "")[:200] + "..." if len(os.environ.get("PATH", "")) > 200 else os.environ.get("PATH", "")
            }
        }
    except Exception as e:
        return {
            "error": f"获取环境信息失败: {str(e)}",
            "platform": platform.system()
        }
