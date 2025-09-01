"""
版本管理配置
"""

# 当前应用版本
CURRENT_VERSION = "1.25.7"

# 版本描述
VERSION_DESCRIPTION = "Pinchy - Python、Node.js脚本调度执行系统"

# 版本历史记录
VERSION_HISTORY = {
    "1.25.7": {
        "release_date": "2025-09-01",
        "description": "优化任务管理界面、下次运行时间",
        "features": [
            "“任务管理”页面分组按钮改为TAB标签页形式，优化间距和圆角效果",
            "“任务管理”页面下次运行时间由后端实时，提高准确性"
        ],
        "bug_fixes": [
            "修复“下次运行时间”计算逻辑，确保前后端一致性"
        ]
    },
    "1.25.6": {
        "release_date": "2025-06-30",
        "description": "新增脚本调试与秒级Cron、企微应用通知",
        "features": [
            "“文件管理”页面新增Pyhton和Node.js脚本调试功能，并实现调试时代码高亮功能",
            "“任务管理”页面新增任务和编辑任务支持秒级Cron表达式",
            "“任务管理”页面分组列表颜色修改为主题配色",
            "“任务管理”页面操作列文字颜色统一为主题配色",
            "“任务管理”页面任务分组列表样式统一",
            "“任务管理”页面任务分组新增横向进度条，分组列表太长时将不再换行显示",
            "“文件管理”页面完善分组显示，隐藏占位任务",
            "“文件管理”页面操作列去除按钮，修改为文字",
            "“文件管理”页面增加刷新列表功能",
            "“脚本订阅”页面操作列文字颜色统一为主题配色，去除图标（“同步”功能保留图标，因为有状态变化）",
            "“环境变量”页面操作列文字颜色统一为主题配色",
            "“环境变量”页面新增复制变量名功能",
            "“系统设置”页面支持查看历史版本更新内容",
            "“系统设置”页面包管理器支持自定义完整路径",
            "“通知服务”页面新增“企业微信应用通知”推送方式",
            "“通知服务”页面增加任务列表分页功能",
            "“通知服务”页面增加刷新任务列表按钮"
        ],
        "bug_fixes": [
            "修复了创建任务分组列表后，下拉选项列表没有立即更新的问题",
            "修复了分组列表“新建”按钮错位的问题",
            "修复了重复设置脚本工作目录的问题（这个BUG可能会导致部分脚本强制在scripts目录运行，而不是在脚本本身所在的目录运行）",
            "修复了首页任务统计没有过滤占位任务的问题"
        ]
    },
    "1.25.5": {
        "release_date": "2025-06-25",
        "description": "优化页面逻辑和新增备份恢复功能",
        "features": [
            "“任务管理”页面新增列表分页功能",
            "“任务管理”页面新增任务分组功能",
            "“脚本订阅”新增自动创建任务开关",
            "“脚本订阅”新增Python脚本文件新增和更新时推送脚本内描述文字",
            "新增任务统计接口用于统计首页的任务数据，避免使用分页获取数据耗时太长",
            "“系统设置”页面新增“备份与恢复”功能，方便Docker用户更新版本迁移数据"
        ],
        "bug_fixes": [
            "修复Docker环境下复制按钮失效的问题",
            "修复“新建订阅”时即使配置了代理，有时仍无法勾选“使用代理”的问题",
            "修复验证码信息析出的问题",
            "修复“时区设置”保存按钮超出屏幕尺寸的问题"
        ]
    },
    "1.25.3": {
        "release_date": "2025-06-19",
        "description": "版本管理自动化、Docker环境Node.js依赖修复和时区管理完善",
        "features": [
            "实现版本号自动更新机制",
            "添加详细的版本历史记录管理",
            "修复Docker环境下Node.js脚本依赖获取问题",
            "优化Node.js脚本执行环境配置",
            "增强版本API返回详细信息",
            "创建统一的时区管理工具模块",
            "新增时区配置API端点",
            "支持常用时区选择和自定义时区",
            "系统信息中显示时区状态"
        ],
        "bug_fixes": [
            "修复硬编码版本号问题",
            "解决Docker环境下NODE_PATH未设置问题",
            "修复Node.js脚本无法访问全局npm包问题",
            "优化脚本执行工作目录配置",
            "改进环境变量传递机制",
            "修复Docker环境下时区显示错误问题",
            "解决任务执行时间显示早8小时的问题",
            "修复所有时间显示使用UTC而非本地时区",
            "统一任务日志和API响应的时间格式"
        ]
    },
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
