# Pinchy - Python、Node.js脚本调度执行系统

Pinchy是一个基于Python+FastAPI开发的脚本调度执行系统，支持通过cron表达式调度执行Python和Node.js脚本。
支持Windows、Linux、Docker多种部署方式。

## 功能特性

- 🔐 **单用户认证系统** - 密码登录保护、多因素验证、账户安全策略
- 📁 **文件管理** - 上传、删除、管理scripts目录下的脚本文件
- ⏰ **任务调度** - 使用cron表达式配置任务执行时间
- 📊 **实时日志** - WebSocket实时查看任务执行日志
- 🌍 **环境变量管理** - 为脚本配置环境变量
- 📦 **包管理** - 安装和删除Python/Node.js依赖包
- 💾 **数据持久化** - 使用SQLite存储所有配置和日志
- 🎨 **现代化界面** - TailwindCSS+响应式设计，完美适配移动端

## 系统要求

- Python 3.10+
- Node.js (如需执行Node.js脚本)
- Git （用于获取脚本订阅）

## 安装和运行

### 1. Windows安装/运行

1. 程序运行需要安装上述环境，如缺失环境请先下载并运行环境安装器Env_installer.exe，83.3MB，[123Pan](https://www.123865.com/s/OnXkjv-nU3BA) / [蓝奏](https://wwqq.lanzoub.com/iP1FW2yzwwvc)
2. 在发行版页面下载含启动器的程序包[Pinchy_1.25.1_Win64_Launcher.zip](https://github.com/3ixi/Pinchy/releases)
3. 解压下载的文件
4. 运行pinchy-launcher.exe
5. 配置运行端口和选择是否开启外部访问（开启后才能通过其他设备访问）
6. 点击“启动服务”按钮等待启动完成，窗口右侧会显示启动状态（显示“Application startup complete.”即表示启动完成）
7. 访问系统地址，默认端口为8000，如http://127.0.0.1:8000

### 2. Docker安装/运行

1. 确保已安装Docker
   ```bash
   docker --version
   ```

2. 拉取Pinchy镜像
   ```bash
   docker pull crpi-9kf3ygmifxk82biy.cn-chengdu.personal.cr.aliyuncs.com/pinchy/pinchy:latest
   ```

3. 运行Docker容器
   ```bash
   docker run -d \
     --name pinchy \
     -p 8000:8000 \
     -v pinchy-data:/app/data \
     -v pinchy-scripts:/app/scripts \
     3ixi/pinchy:latest
   ```

4. 访问系统地址，默认端口为8000，如http://服务器IP:8000

5. 查看容器日志
   ```bash
   docker logs -f pinchy
   ```

6. 停止和重启容器
   ```bash
   # 停止容器
   docker stop pinchy

   # 重启容器
   docker start pinchy
   ```

### 3. Linux安装/运行

1. 确保已安装Python 3.10+、Node.js和Git
   ```bash
   # 检查Python版本
   python3 --version
   # 检查Node.js版本
   node --version
   # 检查Git版本
   git --version
   ```

2. 下载最新版本的Pinchy
   ```bash
   git clone https://github.com/3iXi/Pinchy.git
   cd Pinchy
   ```

3. 创建并使用启动脚本（将以下内容保存为`start.sh`）
   ```bash
   #!/bin/bash

   # 检查并安装必要环境
   check_and_install() {
     echo "检查系统环境..."

     # 检查Python
     if ! command -v python3 &> /dev/null; then
       echo "Python未安装，正在安装Python 3..."
       sudo apt update && sudo apt install -y python3 python3-pip
     fi

     # 检查Node.js
     if ! command -v node &> /dev/null; then
       echo "Node.js未安装，正在安装Node.js..."
       curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
       sudo apt install -y nodejs
     fi

     # 检查Git
     if ! command -v git &> /dev/null; then
       echo "Git未安装，正在安装Git..."
       sudo apt update && sudo apt install -y git
     fi

     # 安装Python依赖
     echo "安装Python依赖..."
     pip3 install -r requirements.txt
   }

   # 启动Pinchy
   start_pinchy() {
     echo "启动Pinchy服务..."
     # 使用nohup后台运行，输出重定向到日志文件
     nohup python3 run.py > pinchy.log 2>&1 &
     echo "Pinchy已在后台启动，进程ID: $!"
     echo "可以使用 'tail -f pinchy.log' 查看实时日志"
     echo "可以使用 'ps aux | grep run.py' 查看进程状态"
   }

   # 停止Pinchy服务
   stop_pinchy() {
     echo "正在停止Pinchy服务..."
     pkill -f "python3 run.py"
     echo "Pinchy服务已停止"
   }

   # 主函数
   main() {
     case "$1" in
       start)
         check_and_install
         start_pinchy
         ;;
       stop)
         stop_pinchy
         ;;
       restart)
         stop_pinchy
         sleep 2
         check_and_install
         start_pinchy
         ;;
       *)
         echo "用法: $0 {start|stop|restart}"
         echo "  start   - 启动Pinchy服务"
         echo "  stop    - 停止Pinchy服务"
         echo "  restart - 重启Pinchy服务"
         exit 1
         ;;
     esac
   }

   main "$@"
   ```

4. 赋予启动脚本执行权限并运行
   ```bash
   chmod +x start.sh
   # 启动服务
   ./start.sh start
   # 查看实时日志
   tail -f pinchy.log
   ```

5. 服务管理命令
   ```bash
   # 启动服务
   ./start.sh start

   # 停止服务
   ./start.sh stop

   # 重启服务
   ./start.sh restart

   # 查看服务状态
   ps aux | grep run.py

   # 查看实时日志
   tail -f pinchy.log
   ```

6. 访问系统地址，默认端口为8000，如http://服务器IP:8000

**⚠️ 首次登录后请立即修改默认密码！**

## 使用指南

### 1. 文件管理

- 在"文件管理"页面上传Python(.py)或Node.js(.js)脚本，并点击复制路径按钮
- 支持创建目录和脚本文件
- 可以在线预览、编辑、下载、删除文件

### 2. 任务管理

- 在"任务管理"页面创建新任务
- 配置任务信息:
  - 任务名称和描述
  - 脚本路径（粘贴刚才复制的脚本路径）
  - 脚本类型（python或nodejs）
  - Cron表达式（如: `0 */1 * * *` 表示每小时整点运行一次）可通过生成器快速生成Cron表达式

### 3. 环境变量

- 在"环境变量"页面管理全局环境变量
- 脚本可以通过`os.environ`(Python)或`process.env`(Node.js)访问
- 脚本可通过判断环境变量pinchyX是否有值来判断是否在Pinchy中运行

### 4. 包管理

- 在"包管理"页面安装Python或Node.js包
- 支持指定版本安装
- 查看已安装包列表

### 5. 执行日志

- 在"执行日志"页面查看任务执行历史
- 支持按任务和状态过滤日志

### 6. 脚本订阅

- 在"脚本订阅"页面添加Git订阅链接
- 支持添加多个订阅链接
- 支持使用代理获取订阅

### 7.通知服务
- 在"通知服务"页面配置通知服务
- 支持使用邮件、Telegram、钉钉、企微、Bark、Server酱、PushPlus、WxPusher等多种通知方式
- 支持配置通知发送条件（如只在任务失败时发送）
- 支持关键词监控
- 集成SendNotify模块，可直接在脚本中调用send(标题, 内容)使用选择的通知方式发送通知

### 8.接口调试
- 在"接口调试"页面可以调试接口，支持POST、GET请求方式
- 支持定时获取接口数据
- 支持使用通知服务推送接口数据
- 支持使用cURL/fetch语法导入接口数据
- 支持在请求中使用部分变量（时间戳、随机数、环境变量）

### 9.系统设置
- 在"系统设置"页面可以配置系统参数
- 支持在线检查版本更新和查看更新内容
- 支持配置账户安全策略（包括多因素认证）
- 提供多种配色主题方案（包括深色模式）
- 支持修改Python/Node.js运行命令路径和包管理器


## 项目结构

```
Pinchy/
├── app/                      # 应用核心代码
│   ├── main.py               # FastAPI应用入口
│   ├── database.py           # 数据库配置
│   ├── models.py             # 数据库模型
│   ├── auth.py               # 登录认证模块
│   ├── scheduler.py          # 任务调度器
│   ├── websocket.py          # WebSocket管理（已弃用）
│   ├── websocket_manager.py  # WebSocket连接管理
│   └── routers/              # API路由
├── static/                   # 静态文件
│   ├── index.html            # 前端页面
│   ├── css/tailwind.min.css  # 前端样式表（已构建）
│   ├── images\favicon.ico    # 图标
│   ├── images\logo.png       # Logo
│   ├── js/app.js             # 前端逻辑
├── scripts/                  # 用户脚本存储目录
│   ├── SendNotify.py         # 通知模块
├── logs/                     # 日志文件目录(启动器使用)
├── requirements.txt          # Python依赖
├── run.py                    # 启动脚本
└── README.md                 # 说明文档
```

## 技术栈

- **后端**: Python, FastAPI, SQLAlchemy, APScheduler
- **数据库**: SQLite
- **前端**: HTML, TailwindCSS, Alpine.js
- **实时通信**: WebSockets

## 安全注意事项

1. 务必修改app/auth.py中23行的SECRET_KEY第二个引号中的内容为随机字符串
[![20250618631d320250618121340891.png](https://kycloud3.koyoo.cn/20250618631d320250618121340891.png)](https://kycloud3.koyoo.cn/20250618631d320250618121340891.png)
2. 修改默认管理员密码
3. 确保scripts目录的访问权限设置正确
4. 定期备份数据库文件(pinchy.db)

## 故障排除

### 常见问题

1. **任务不执行**
   - 检查cron表达式格式是否正确
   - 确认任务状态为"启用"
   - 查看执行日志中的错误信息

2. **脚本执行失败**
   - 确认Python/Node.js环境已正确安装
   - 检查脚本路径是否正确
   - 查看错误日志排查脚本问题

3. **WebSocket连接失败**
   - 检查防火墙设置
   - 确认浏览器支持WebSocket

## 运行截图
[![20250618e72bc202506181147087615.png](https://kycloud3.koyoo.cn/20250618e72bc202506181147087615.png)](https://kycloud3.koyoo.cn/20250618e72bc202506181147087615.png)
[![20250618dadad202506181147082730.png](https://kycloud3.koyoo.cn/20250618dadad202506181147082730.png)](https://kycloud3.koyoo.cn/20250618dadad202506181147082730.png)
[![202506187cfd9202506181147087167.png](https://kycloud3.koyoo.cn/202506187cfd9202506181147087167.png)](https://kycloud3.koyoo.cn/202506187cfd9202506181147087167.png)
[![20250618011a9202506181147089841.png](https://kycloud3.koyoo.cn/20250618011a9202506181147089841.png)](https://kycloud3.koyoo.cn/20250618011a9202506181147089841.png)
[![20250618909dd20250618114709639.png](https://kycloud3.koyoo.cn/20250618909dd20250618114709639.png)](https://kycloud3.koyoo.cn/20250618909dd20250618114709639.png)
[![2025061841c68202506181152267133.png](https://kycloud3.koyoo.cn/2025061841c68202506181152267133.png)](https://kycloud3.koyoo.cn/2025061841c68202506181152267133.png)
[![20250613bb987202506131741238786.png](https://kycloud3.koyoo.cn/20250613bb987202506131741238786.png)](https://kycloud3.koyoo.cn/20250613bb987202506131741238786.png)
[![2025061803fd4202506181147085842.png](https://kycloud3.koyoo.cn/2025061803fd4202506181147085842.png)](https://kycloud3.koyoo.cn/2025061803fd4202506181147085842.png)