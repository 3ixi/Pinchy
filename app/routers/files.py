"""
文件管理相关路由
"""
import os
import shutil
import zipfile
import tarfile
import gzip
import stat
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.auth import get_current_user
from app.models import User

router = APIRouter(prefix="/api/files", tags=["文件管理"])

class FileInfo(BaseModel):
    name: str
    path: str
    size: int
    is_directory: bool
    modified_time: str

class DirectoryContent(BaseModel):
    files: List[FileInfo]
    current_path: str

class SaveFileRequest(BaseModel):
    path: str
    content: str

class CreateTextFileRequest(BaseModel):
    filename: str
    content: str
    path: str = ""

SCRIPTS_DIR = "scripts"

def ensure_scripts_dir():
    """确保scripts目录存在"""
    if not os.path.exists(SCRIPTS_DIR):
        os.makedirs(SCRIPTS_DIR)

def is_safe_path(path: str) -> bool:
    """检查路径是否安全（防止目录遍历攻击）"""
    try:
        # 规范化路径
        normalized_path = os.path.normpath(path)
        # 检查是否在scripts目录内
        return normalized_path.startswith(SCRIPTS_DIR) or normalized_path == SCRIPTS_DIR
    except:
        return False

def force_remove_readonly(func, path, exc):
    """强制删除只读文件的错误处理函数"""
    if os.path.exists(path):
        # 移除只读属性
        os.chmod(path, stat.S_IWRITE)
        # 重新尝试删除
        func(path)

def force_remove_tree(path):
    """强制删除目录树，包括只读文件"""
    try:
        # 首先尝试正常删除
        shutil.rmtree(path)
    except (OSError, PermissionError):
        # 如果失败，使用强制删除
        shutil.rmtree(path, onerror=force_remove_readonly)

@router.get("/list", response_model=DirectoryContent)
async def list_files(path: str = "", current_user: User = Depends(get_current_user)):
    """列出文件和目录"""
    ensure_scripts_dir()
    
    # 构建完整路径
    if path:
        full_path = os.path.join(SCRIPTS_DIR, path)
    else:
        full_path = SCRIPTS_DIR
    
    # 安全检查
    if not is_safe_path(full_path):
        raise HTTPException(status_code=400, detail="无效的路径")
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="路径不存在")
    
    if not os.path.isdir(full_path):
        raise HTTPException(status_code=400, detail="路径不是目录")
    
    files = []
    try:
        for item in os.listdir(full_path):
            item_path = os.path.join(full_path, item)
            relative_path = os.path.relpath(item_path, SCRIPTS_DIR)
            
            stat = os.stat(item_path)
            files.append(FileInfo(
                name=item,
                path=relative_path,
                size=stat.st_size,
                is_directory=os.path.isdir(item_path),
                modified_time=str(stat.st_mtime)
            ))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取目录失败: {str(e)}")
    
    return DirectoryContent(files=files, current_path=path)

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    path: str = Form(""),
    current_user: User = Depends(get_current_user)
):
    """上传文件"""
    ensure_scripts_dir()
    
    # 构建目标路径
    if path:
        target_dir = os.path.join(SCRIPTS_DIR, path)
    else:
        target_dir = SCRIPTS_DIR
    
    # 安全检查
    if not is_safe_path(target_dir):
        raise HTTPException(status_code=400, detail="无效的路径")
    
    # 确保目标目录存在
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    
    # 构建完整文件路径
    file_path = os.path.join(target_dir, file.filename)
    
    # 检查文件是否已存在
    if os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="文件已存在")
    
    try:
        # 保存文件
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        return {"message": f"文件 {file.filename} 上传成功", "path": os.path.relpath(file_path, SCRIPTS_DIR)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传文件失败: {str(e)}")

@router.delete("/delete")
async def delete_file(path: str, current_user: User = Depends(get_current_user)):
    """删除文件或目录"""
    full_path = os.path.join(SCRIPTS_DIR, path)

    # 安全检查
    if not is_safe_path(full_path):
        raise HTTPException(status_code=400, detail="无效的路径")

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="文件或目录不存在")

    try:
        if os.path.isdir(full_path):
            # 使用强制删除来处理只读文件
            force_remove_tree(full_path)
            return {"message": f"目录 {path} 删除成功"}
        else:
            # 对于单个文件，也可能是只读的
            try:
                os.remove(full_path)
            except (OSError, PermissionError):
                # 如果删除失败，尝试移除只读属性后再删除
                os.chmod(full_path, stat.S_IWRITE)
                os.remove(full_path)
            return {"message": f"文件 {path} 删除成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@router.post("/create-directory")
async def create_directory(
    name: str = Form(...),
    path: str = Form(""),
    current_user: User = Depends(get_current_user)
):
    """创建目录"""
    ensure_scripts_dir()
    
    # 构建目标路径
    if path:
        parent_dir = os.path.join(SCRIPTS_DIR, path)
    else:
        parent_dir = SCRIPTS_DIR
    
    new_dir_path = os.path.join(parent_dir, name)
    
    # 安全检查
    if not is_safe_path(new_dir_path):
        raise HTTPException(status_code=400, detail="无效的路径")
    
    if os.path.exists(new_dir_path):
        raise HTTPException(status_code=400, detail="目录已存在")
    
    try:
        os.makedirs(new_dir_path)
        return {"message": f"目录 {name} 创建成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建目录失败: {str(e)}")

@router.get("/download")
async def download_file(path: str, current_user: User = Depends(get_current_user)):
    """下载文件"""
    full_path = os.path.join(SCRIPTS_DIR, path)

    # 安全检查
    if not is_safe_path(full_path):
        raise HTTPException(status_code=400, detail="无效的路径")

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    if os.path.isdir(full_path):
        raise HTTPException(status_code=400, detail="无法下载目录")

    return FileResponse(
        path=full_path,
        filename=os.path.basename(full_path),
        media_type='application/octet-stream'
    )

@router.get("/preview")
async def preview_file(path: str, current_user: User = Depends(get_current_user)):
    """预览文件内容"""
    full_path = os.path.join(SCRIPTS_DIR, path)

    # 安全检查
    if not is_safe_path(full_path):
        raise HTTPException(status_code=400, detail="无效的路径")

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    if os.path.isdir(full_path):
        raise HTTPException(status_code=400, detail="无法预览目录")

    try:
        # 检查文件大小，避免预览过大的文件
        file_size = os.path.getsize(full_path)
        if file_size > 1024 * 1024:  # 1MB
            raise HTTPException(status_code=400, detail="文件过大，无法预览")

        # 尝试读取文件内容
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return {"content": content, "size": file_size}
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="文件不是文本格式，无法预览")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预览文件失败: {str(e)}")

@router.post("/rename")
async def rename_file(
    old_path: str = Form(...),
    new_name: str = Form(...),
    current_user: User = Depends(get_current_user)
):
    """重命名文件或目录"""
    old_full_path = os.path.join(SCRIPTS_DIR, old_path)

    # 安全检查
    if not is_safe_path(old_full_path):
        raise HTTPException(status_code=400, detail="无效的路径")

    if not os.path.exists(old_full_path):
        raise HTTPException(status_code=404, detail="文件或目录不存在")

    # 构建新路径
    parent_dir = os.path.dirname(old_full_path)
    new_full_path = os.path.join(parent_dir, new_name)

    # 检查新路径是否安全
    if not is_safe_path(new_full_path):
        raise HTTPException(status_code=400, detail="无效的新名称")

    # 检查新名称是否已存在
    if os.path.exists(new_full_path):
        raise HTTPException(status_code=400, detail="新名称已存在")

    try:
        os.rename(old_full_path, new_full_path)
        return {"message": f"重命名成功", "new_path": os.path.relpath(new_full_path, SCRIPTS_DIR)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重命名失败: {str(e)}")

@router.post("/save")
async def save_file(
    save_request: SaveFileRequest,
    current_user: User = Depends(get_current_user)
):
    """保存文件内容"""
    full_path = os.path.join(SCRIPTS_DIR, save_request.path)

    # 安全检查
    if not is_safe_path(full_path):
        raise HTTPException(status_code=400, detail="无效的路径")

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    if os.path.isdir(full_path):
        raise HTTPException(status_code=400, detail="无法保存目录")

    try:
        # 保存文件内容
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(save_request.content)

        return {"message": f"文件 {save_request.path} 保存成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存文件失败: {str(e)}")

@router.post("/extract")
async def extract_archive(
    path: str = Form(...),
    current_user: User = Depends(get_current_user)
):
    """解压压缩文件"""
    full_path = os.path.join(SCRIPTS_DIR, path)

    # 安全检查
    if not is_safe_path(full_path):
        raise HTTPException(status_code=400, detail="无效的路径")

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    if os.path.isdir(full_path):
        raise HTTPException(status_code=400, detail="无法解压目录")

    # 获取文件扩展名
    filename = os.path.basename(full_path).lower()

    # 检查是否为支持的压缩格式
    if not (filename.endswith('.zip') or filename.endswith('.tar.gz') or
            filename.endswith('.tgz') or filename.endswith('.gz')):
        raise HTTPException(status_code=400, detail="不支持的压缩格式，仅支持 zip、tar.gz、gz 格式")

    # 解压目标目录（与压缩文件同级目录）
    extract_dir = os.path.dirname(full_path)

    try:
        extracted_files = []

        if filename.endswith('.zip'):
            # 解压ZIP文件
            with zipfile.ZipFile(full_path, 'r') as zip_ref:
                # 安全检查：防止路径遍历攻击
                for member in zip_ref.namelist():
                    if os.path.isabs(member) or ".." in member:
                        raise HTTPException(status_code=400, detail=f"压缩文件包含不安全的路径: {member}")

                # 解压所有文件
                zip_ref.extractall(extract_dir)
                extracted_files = zip_ref.namelist()

        elif filename.endswith(('.tar.gz', '.tgz')):
            # 解压TAR.GZ文件
            with tarfile.open(full_path, 'r:gz') as tar_ref:
                # 安全检查：防止路径遍历攻击
                for member in tar_ref.getnames():
                    if os.path.isabs(member) or ".." in member:
                        raise HTTPException(status_code=400, detail=f"压缩文件包含不安全的路径: {member}")

                # 解压所有文件
                tar_ref.extractall(extract_dir)
                extracted_files = tar_ref.getnames()

        elif filename.endswith('.gz') and not filename.endswith('.tar.gz'):
            # 解压单个GZ文件
            output_filename = filename[:-3]  # 移除.gz扩展名
            output_path = os.path.join(extract_dir, output_filename)

            with gzip.open(full_path, 'rb') as gz_file:
                with open(output_path, 'wb') as output_file:
                    shutil.copyfileobj(gz_file, output_file)

            extracted_files = [output_filename]

        return {
            "message": f"解压成功，共解压 {len(extracted_files)} 个文件",
            "extracted_files": extracted_files[:10],  # 最多显示前10个文件名
            "total_count": len(extracted_files)
        }

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="无效的ZIP文件")
    except tarfile.TarError:
        raise HTTPException(status_code=400, detail="无效的TAR文件")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解压失败: {str(e)}")

@router.post("/create-text")
async def create_text_file(
    request: CreateTextFileRequest,
    current_user: User = Depends(get_current_user)
):
    """创建文本文件"""
    ensure_scripts_dir()

    # 构建目标路径
    if request.path:
        target_dir = os.path.join(SCRIPTS_DIR, request.path)
    else:
        target_dir = SCRIPTS_DIR

    # 安全检查
    if not is_safe_path(target_dir):
        raise HTTPException(status_code=400, detail="无效的路径")

    # 确保目标目录存在
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    # 构建完整文件路径
    file_path = os.path.join(target_dir, request.filename)

    # 安全检查
    if not is_safe_path(file_path):
        raise HTTPException(status_code=400, detail="无效的文件名")

    # 检查文件是否已存在
    if os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="文件已存在")

    try:
        # 创建文件并写入内容
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(request.content)

        return {
            "message": f"文件 {request.filename} 创建成功",
            "path": os.path.relpath(file_path, SCRIPTS_DIR)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建文件失败: {str(e)}")
