#!/bin/bash
# VedaAide VM 首次初始化脚本
# 在 Oracle Cloud VM 上以 opc 用户执行一次即可。
# 不需要安装任何软件——python3/venv/rsync 已预装在 Oracle Linux 9 中。
#
# 用法（在 VM 上执行）:
#   bash setup_vm.sh

set -e

PROJECT_PATH="/home/opc/VedaAide"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log()     { echo -e "${BLUE}[setup]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }

# 创建项目目录（rsync 推送前需要存在）
log "创建项目目录..."
mkdir -p "$PROJECT_PATH"
mkdir -p "$PROJECT_PATH/data"
mkdir -p "$PROJECT_PATH/logs"
success "目录已创建: $PROJECT_PATH"

# 创建 .env 占位文件
if [ ! -f "$PROJECT_PATH/.env" ]; then
    touch "$PROJECT_PATH/.env"
    success ".env 已创建（首次部署后会自动写入密钥）"
else
    log ".env 已存在，跳过"
fi

echo ""
success "VM 初始化完成！"
echo ""
echo "接下来："
echo "  1. 在 GitHub 仓库配置以下 Secrets："
echo "       ORACLE_SSH_PRIVATE_KEY  — 本机 ~/.ssh/vedaaide_deploy 私钥内容"
echo "       ORACLE_SSH_USER         — opc"
echo "       ORACLE_SERVER_IP        — 130.162.193.156"
echo "       ORACLE_PROJECT_PATH     — /home/opc/VedaAide"
echo "       DEEPSEEK_API_KEY        — DeepSeek API Key"
echo "       TELEGRAM_BOT_TOKEN      — Telegram Bot Token"
echo ""
echo "  2. 推送代码到 main 分支即可触发自动部署。"
echo "     首次部署会自动创建 venv 并安装依赖，约需 1-2 分钟。"
