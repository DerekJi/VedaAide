FROM python:3.11-slim

WORKDIR /workspace

# 先复制依赖清单，利用 Docker 层缓存加速重建
COPY bot_app/requirements.txt /workspace/requirements.txt

RUN pip install --no-cache-dir -r /workspace/requirements.txt

# 复制项目代码（在 compose 中使用仓库根目录作为 build context）
COPY . /workspace/

RUN mkdir -p /workspace/data /workspace/logs

CMD ["python", "-m", "bot_app.main"]
