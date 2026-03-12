# CI/CD 部署指南

## 📋 概述

VedaAide 采用 **GitHub Actions + Oracle Cloud** 的自动化部署方案：

- 每次 push 到 `main` 分支时自动触发部署
- 支持手动触发部署
- 自动备份数据
- 健康检查和回滚机制
- Slack 通知（可选）

---

## 🔧 前置准备

### 1. Oracle Cloud VM 配置

**需要安装以下工具：**

```bash
# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 安装 Git
sudo apt-get update
sudo apt-get install -y git

# 克隆项目
git clone https://github.com/YOUR_USERNAME/VedaAide.git
cd VedaAide
```

**创建部署用户（可选但推荐）：**

```bash
# 创建专用部署用户
sudo useradd -m -s /bin/bash vedaaide
sudo usermod -aG docker vedaaide

# 配置 sudoers（如果需要）
echo "vedaaide ALL=(ALL) NOPASSWD: /usr/bin/docker-compose" | sudo tee /etc/sudoers.d/vedaaide
```

---

## 🔑 配置 GitHub Secrets

### 访问 GitHub Secrets 配置页面

1. 进入 GitHub 仓库
2. 点击 **Settings** → **Secrets and variables** → **Actions**
3. 点击 **New repository secret**

### 必需的 Secrets

添加以下 Secrets：

| Secret 名称 | 说明 | 示例 |
|-----------|------|------|
| `ORACLE_SSH_PRIVATE_KEY` | Oracle VM SSH 私钥 | `-----BEGIN RSA PRIVATE KEY-----...` |
| `ORACLE_SSH_USER` | SSH 用户名 | `vedaaide` 或 `ubuntu` |
| `ORACLE_SERVER_IP` | Oracle VM 公网IP | `152.69.85.123` |
| `ORACLE_PROJECT_PATH` | 项目在服务器上的路径 | `/home/vedaaide/VedaAide` |

### 可选的 Secrets（用于通知）

| Secret 名称 | 说明 |
|-----------|------|
| `SLACK_WEBHOOK_URL` | Slack webhook 地址（用于部署通知） |

---

## 📝 配置 SSH 密钥

### 方式1：使用现有的 SSH 密钥

如果已拥有 Oracle VM 的 SSH 密钥：

```bash
# 查看私钥内容
cat ~/.ssh/oracle_private_key

# 复制完整内容到 GitHub Secrets 中的 ORACLE_SSH_PRIVATE_KEY
```

### 方式2：生成新的 SSH 密钥对

```bash
# 在本地生成
ssh-keygen -t rsa -b 4096 -f ~/.ssh/vedaaide_deploy -N ""

# 查看私钥（复制到 GitHub Secrets）
cat ~/.ssh/vedaaide_deploy

# 将公钥添加到 Oracle VM
ssh ubuntu@YOUR_ORACLE_IP << 'EOF'
mkdir -p ~/.ssh
echo "$(cat ~/.ssh/vedaaide_deploy.pub)" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
EOF
```

---

## 🚀 部署流程

### 自动部署（推荐）

只需将代码 push 到 `main` 分支：

```bash
git add .
git commit -m "feat: add new skill"
git push origin main
```

GitHub Actions 会自动：
1. ✅ 拉取最新代码
2. ✅ 备份数据
3. ✅ 停止现有服务
4. ✅ 拉取最新容器镜像
5. ✅ 启动新服务
6. ✅ 执行健康检查
7. ✅ 发送 Slack 通知（可选）

### 手动触发部署

进入 GitHub Actions 选项卡 → 选择 **Deploy to Oracle Cloud** → 点击 **Run workflow** → 选择 `main` 分支 → 确认

---

## 📊 监控部署

### 在 GitHub 查看部署日志

1. 进入仓库 → **Actions** 选项卡
2. 点击最新的 **Deploy to Oracle Cloud** 工作流程
3. 展开 **Deploy to Oracle Cloud** job 查看日志

### 在 Oracle VM 查看部署日志

```bash
# SSH 连接到服务器
ssh -i ~/.ssh/oracle_private_key vedaaide@YOUR_ORACLE_IP

# 查看最近的部署日志
tail -f /home/vedaaide/VedaAide/backups/deploy_*.log

# 查看 Docker 容器日志
cd ~/VedaAide
docker-compose logs -f vedaaide-bot  # 查看 Bot 核心日志
docker-compose logs -f vedaaide-db   # 查看数据库日志
```

---

## 💾 数据备份与恢复

### 自动备份

部署脚本会自动在 `backups/` 目录中创建备份：

```bash
# 查看备份列表
ls -lh /home/vedaaide/VedaAide/backups/

# 备份文件命名格式
data_20260311_120000.tar.gz           # 生活事件数据
chroma_data_20260311_120000.tar.gz    # ChromaDB 向量数据
```

### 手动恢复备份

```bash
cd /home/vedaaide/VedaAide

# 停止服务
docker-compose down

# 恢复数据
tar -xzf backups/data_20260311_120000.tar.gz
tar -xzf backups/chroma_data_20260311_120000.tar.gz

# 重新启动
docker-compose up -d
```

---

## 🔄 环境变量配置

### 创建 .env 文件

在服务器项目根目录创建 `.env` 文件：

```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN

# DeepSeek API
DEEPSEEK_API_KEY=YOUR_DEEPSEEK_API_KEY
DEEPSEEK_MODEL=deepseek-chat

# 数据库（Bot 直连 SQLite，无需 HTTP 服务）
DB_PATH=/app/data/vedaaide.db

# 时区
TZ=Asia/Shanghai
```

**重要：** `.env` 文件中的机密信息不应提交到 Git。在 `.gitignore` 中已排除：

```bash
# .gitignore
.env
.env.local
```

---

## 🛠️ 故障排除

### 故障：SSH 连接失败

```bash
# 检查 SSH 密钥权限
chmod 600 ~/.ssh/oracle_private_key

# 测试 SSH 连接
ssh -i ~/.ssh/oracle_private_key -v vedaaide@YOUR_ORACLE_IP
```

### 故障：容器启动失败

```bash
# 查看容器日志
docker-compose logs vedaaide-bot

# 查看 Docker 错误
docker ps -a
docker inspect CONTAINER_ID
```

### 故障：后续部署中数据丢失

确保 `.env` 中配置了正确的数据卷路径，`docker-compose.yml` 中的 `volumes` 指向正确的主机路径。

---

## 📈 最佳实践

### 1. 分支策略

```
main       ← 稳定生产分支（自动部署）
develop    ← 开发分支（本地测试）
feature/*  ← 功能分支（PR 后合并）
```

### 2. 提交信息规范（Conventional Commits）

```bash
git commit -m "feat: add record_event_skill"
git commit -m "fix: fix Ollama timeout issue"
git commit -m "docs: update deployment guide"
```

### 3. 部署前检查清单

- [ ] 在本地测试通过
- [ ] 代码审查（PR）完成
- [ ] 更新相关文档
- [ ] 检查 `.env` 配置
- [ ] 确保备份可用

## 🔐 安全建议

- ✅ 定期轮换 SSH 密钥
- ✅ 使用强密码保护 SSH 密钥
- ✅ 定期审查 GitHub Secrets
- ✅ 不要将机密信息提交到 Git
- ✅ 使用 VPC 和安全组限制 Oracle VM 访问
- ✅ 启用 GitHub 的分支保护规则（在 main 分支上要求 PR 审查）

---

## 📞 常见问题

**Q: 部署失败会回滚吗？**
A: 目前的脚本不会自动回滚。建议部署前进行备份，并在部署日志中查看具体错误。后续可添加自动回滚机制。

**Q: 可以部署到多个服务器吗？**
A: 可以。在 GitHub Secrets 中添加多个 `ORACLE_SERVER_IP` 变量，并在 workflow 中配置矩阵策略。

**Q: 如何跳过某次自动部署？**
A: 在提交信息中添加 `[skip ci]`：
```bash
git commit -m "docs: update README [skip ci]"
```

---

更新日期：2026-03-11
