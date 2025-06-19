FROM python:3.11-slim

# 安装系统依赖项
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 Node.js (LTS 版本)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest

WORKDIR /app

COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 创建必要的目录
RUN mkdir -p logs scripts static

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHON_COMMAND=python3
ENV NODEJS_COMMAND=node
ENV NODE_PATH=/usr/local/lib/node_modules
ENV NPM_CONFIG_PREFIX=/usr/local
ENV SECRET_KEY=1b3c86abc6a54741b6f29d89d5148e42_pinchy

EXPOSE 8000

CMD ["python", "run.py"]