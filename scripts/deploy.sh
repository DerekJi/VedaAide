#!/bin/bash

# VedaAide 部署脚本
# 用途：在 Oracle Cloud 服务器上执行，由 GitHub Actions 调用

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
PROJECT_PATH="${PROJECT_PATH:-.}"
BACKUP_DIR="${PROJECT_PATH}/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${BACKUP_DIR}/deploy_${TIMESTAMP}.log"

# 日志函数
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[✓]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[✗] ERROR:${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

warning() {
    echo -e "${YELLOW}[!]${NC} $1" | tee -a "$LOG_FILE"
}

# 初始化
log "=========================================="
log "VedaAide 部署开始"
log "=========================================="
log "项目路径: $PROJECT_PATH"
log "时间戳: $TIMESTAMP"

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 步骤 1: 前置检查
log "\n📋 步骤1: 执行前置检查..."

if [ ! -f "$PROJECT_PATH/docker-compose.yml" ]; then
    error "找不到 docker-compose.yml 文件"
fi
success "docker-compose.yml 存在"

if ! command -v docker &> /dev/null; then
    error "Docker 未安装"
fi
success "Docker 已安装"

if ! command -v docker-compose &> /dev/null; then
    error "Docker Compose 未安装"
fi
success "Docker Compose 已安装"

# 步骤 2: 备份数据
log "\n💾 步骤2: 备份数据..."

if [ -d "$PROJECT_PATH/data" ]; then
    tar -czf "$BACKUP_DIR/data_${TIMESTAMP}.tar.gz" -C "$PROJECT_PATH" data/
    success "已备份 data 目录"
else
    warning "data 目录不存在，跳过备份"
fi

if [ -d "$PROJECT_PATH/chroma_data" ]; then
    tar -czf "$BACKUP_DIR/chroma_data_${TIMESTAMP}.tar.gz" -C "$PROJECT_PATH" chroma_data/
    success "已备份 chroma_data 目录"
else
    warning "chroma_data 目录不存在"
fi

# 清理旧备份（保留最近7个）
log "清理旧备份（保留最近7个）..."
find "$BACKUP_DIR" -name "data_*.tar.gz" -type f -mtime +7 -delete
find "$BACKUP_DIR" -name "chroma_data_*.tar.gz" -type f -mtime +7 -delete
success "旧备份已清理"

# 步骤 3: 拉取最新代码
log "\n📥 步骤3: 拉取最新代码..."

cd "$PROJECT_PATH"
git fetch origin
git reset --hard origin/main
success "代码已更新到最新版本"

# 步骤 4: 加载环境变量
log "\n⚙️  步骤4: 加载环境变量..."

if [ -f "$PROJECT_PATH/.env" ]; then
    set -a
    source "$PROJECT_PATH/.env"
    set +a
    success ".env 文件已加载"
else
    warning ".env 文件不存在，使用默认环境变量"
fi

# 步骤 5: 停止现有服务
log "\n🛑 步骤5: 停止现有服务..."

if docker-compose ps | grep -q "Up"; then
    docker-compose down
    success "服务已停止"
else
    warning "没有运行中的服务"
fi

# 步骤 6: 拉取最新镜像
log "\n📦 步骤6: 拉取最新镜像..."

docker-compose pull
success "镜像已拉取"

# 步骤 7: 启动新服务
log "\n🚀 步骤7: 启动新服务..."

docker-compose up -d
success "服务已启动"

# 步骤 8: 等待服务就绪
log "\n⏳ 步骤8: 等待服务就绪（30秒）..."

sleep 30

# 步骤 9: 健康检查
log "\n🏥 步骤9: 执行健康检查..."

HEALTH_CHECK_PASSED=true

# 检查容器状态
while IFS= read -r line; do
    if echo "$line" | grep -q "Exit\|unhealthy"; then
        HEALTH_CHECK_PASSED=false
        warning "发现不健康的容器: $line"
    fi
done < <(docker-compose ps)

if [ "$HEALTH_CHECK_PASSED" = true ]; then
    success "所有容器运行正常"
else
    error "健康检查失败，请检查容器日志"
fi

# 步骤 10: 清理旧镜像和容器（可选）
log "\n🧹 步骤10: 清理未使用的资源..."

docker image prune -f --filter="dangling=true" > /dev/null 2>&1 || true
docker container prune -f > /dev/null 2>&1 || true
success "资源已清理"

# 完成
log "\n=========================================="
success "✨ VedaAide 部署完成！"
log "部署日志已保存至: $LOG_FILE"
log "=========================================="
