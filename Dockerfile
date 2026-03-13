FROM python:3.11-alpine

WORKDIR /app

# 安装依赖
COPY bot_app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY bot_app/ ./bot_app/

# 数据目录（由 Volume 挂载）
RUN mkdir -p /app/data /app/logs

CMD ["python", "-m", "bot_app.main"]
