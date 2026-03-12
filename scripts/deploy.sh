#!/bin/bash
# VedaAide 部署脚本（无容器版）
# 由 GitHub Actions 通过 SSH 调用（rsync 推送代码后执行），或手动执行。
# 前提：代码已就位（rsync 同步完成），.env 已存在于项目根目录。

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

PROJECT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log()     { echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }
warn()    { echo -e "${YELLOW}[!]${NC} $1"; }
fail()    { echo -e "${RED}[✗]${NC} $1"; exit 1; }

log "=========================================="
log "VedaAide 部署 (systemd 版)"
log "项目路径: $PROJECT_PATH"
log "=========================================="

cd "$PROJECT_PATH"
export PYTHONPATH="$PROJECT_PATH"

# 步骤 1: 创建/更新 venv 并安装依赖
log "📦 安装 Python 依赖..."
python3 -m venv venv
venv/bin/pip install -q --no-cache-dir --upgrade pip
venv/bin/pip install -q --no-cache-dir -r bot_app/requirements.txt
success "依赖安装完成"

# 步骤 2: 安装/更新 systemd service 文件
log "⚙️  更新 systemd service..."
sudo cp scripts/vedaaide.service /etc/systemd/system/vedaaide.service
sudo systemctl daemon-reload
sudo systemctl enable vedaaide --quiet
success "service 文件已更新"

# 步骤 3: 重启服务
log "🔄 重启服务..."
sudo systemctl restart vedaaide || true

# 步骤 4: 健康检查
sleep 5
if sudo systemctl is-active --quiet vedaaide; then
    success "服务运行正常"
    sudo systemctl status vedaaide --no-pager -l | tail -5
else
    log "=== 最近 30 条 journal 日志 ==="
    sudo journalctl -u vedaaide -n 30 --no-pager
    fail "服务启动失败（见上方日志）"
fi

log "=========================================="
success "✨ VedaAide 部署完成！"
log "==========================================
"
