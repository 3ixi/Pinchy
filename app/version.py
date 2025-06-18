"""
版本管理配置
"""

# 当前应用版本
CURRENT_VERSION = "1.25.2"

# 版本描述
VERSION_DESCRIPTION = "Pinchy - Python、Node.js脚本调度执行系统"

# 版本历史记录
VERSION_HISTORY = {
    "1.25.2": {
        "release_date": "2025-06-18",
        "description": "包管理功能优化，Docker环境支持改进",
        "features": [
            "修复Windows环境下Node.js包安装失败问题",
            "改进Docker环境下包列表获取功能",
            "添加多重包检测机制",
            "优化编码兼容性和错误处理"
        ],
        "bug_fixes": [
            "修复包安装成功但列表不显示的问题",
            "解决Docker环境下npm路径不一致问题",
            "修复编码问题导致的解析失败"
        ]
    },
    "1.25.1": {
        "release_date": "2025-06-18",
        "description": "首个版本发布",
        "features": [
            "发布第一个版本"
        ]
    }
}

def get_current_version():
    """获取当前版本号"""
    return CURRENT_VERSION

def get_version_description():
    """获取版本描述"""
    return VERSION_DESCRIPTION

def get_version_info(version=None):
    """获取指定版本的详细信息"""
    if version is None:
        version = CURRENT_VERSION
    return VERSION_HISTORY.get(version, {})

def compare_versions(version1: str, version2: str) -> int:
    """
    比较两个版本号
    返回值：
    -1: version1 < version2
     0: version1 == version2
     1: version1 > version2
    """
    try:
        # 移除版本号前的'v'字符
        v1 = version1.lstrip('v')
        v2 = version2.lstrip('v')
        
        # 分割版本号
        v1_parts = [int(x) for x in v1.split('.')]
        v2_parts = [int(x) for x in v2.split('.')]
        
        # 补齐版本号长度
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_len - len(v1_parts)))
        v2_parts.extend([0] * (max_len - len(v2_parts)))
        
        # 比较版本号
        for i in range(max_len):
            if v1_parts[i] < v2_parts[i]:
                return -1
            elif v1_parts[i] > v2_parts[i]:
                return 1
        
        return 0
    except Exception:
        return 0

def is_newer_version(current: str, new: str) -> bool:
    """检查new版本是否比current版本更新"""
    return compare_versions(current, new) < 0
