FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 安装 Flask 和 SQLite 相关依赖
RUN pip install --no-cache-dir \
    flask==3.0.0 \
    flask-cors==4.0.0 \
    python-dotenv==1.0.0

# 创建简单的 Flask Web API
RUN mkdir -p /app/data

COPY app.py .

EXPOSE 5000

CMD ["python", "app.py"]
