# CI/CD 部署指南

## 📋 概述

VedaAide 采用 **GitHub Actions + Oracle Cloud** 的自动化部署方案：

- 每次 push 到 `main` 分支时自动触发部署
- 支持手动触发部署
- rsync 增量推送源码，VM 上无需安装 git 或 Docker
- systemd 管理进程，崩溃自动重启

---

## 🔧 前置准备

### Oracle Cloud VM 配置

**VM 默认用户是 `opc`（Oracle Linux），不是 `ubuntu`。**

VM 上已预装：python3 / venv / rsync，**无需手动安装任何软件**。

首次初始化只需创建项目目录：

```bash
ssh -i ~/.ssh/vedaaide_deploy opc@YOUR_ORACLE_IP

mkdir -p /home/opc/VedaAide/data /home/opc/VedaAide/logs
touch /home/opc/VedaAide/.env
```

---

## 🔑 配置 GitHub Secrets

**Settings → Secrets and variables → Actions → New repository secret**

| Secret 名称 | 说明 | 值 |
|-----------|------|------|
| `ORACLE_SSH_PRIVATE_KEY` | SSH 私钥 | `cat ~/.ssh/vedaaide_deploy` 全部内容 |
| `ORACLE_SSH_USER` | SSH 用户名 | `opc` |
| `ORACLE_SERVER_IP` | Oracle VM 公网IP | `130.162.193.156` |
| `ORACLE_PROJECT_PATH` | 项目路径 | `/home/opc/VedaAide` |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | — |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | — |

可选：

| Secret 名称 | 说明 |
|-----------|------|
| `SLACK_WEBHOOK_URL` | Slack 部署通知 |

---

## 📝 配置 SSH 密钥

```bash
# 在本地生成
ssh-keygen -t rsa -b 4096 -f ~/.ssh/vedaaide_deploy -N ""

# 查看私钥（复制到 GitHub Secrets）
cat ~/.ssh/vedaaide_deploy
```

公钥在创建 Oracle VM 时已通过控制台配置，无需手动添加到 `authorized_keys`。

---

## 🚀 部署流程

### 自动部署（推荐）

```bash
git add .
git commit -m "feat: add new skill"
git push origin main
```

GitHub Actions 自动执行：
1. ✅ Checkout 代码（在 runner 上）
2. ✅ rsync 推送源码到 VM（增量，几秒完成）
3. ✅ SSH 写入 .env 密钥（不覆盖已有值）
4. ✅ 创建/更新 venv，安装依赖
5. ✅ 更新 systemd service 文件
6. ✅ `systemctl restart vedaaide`
7. ✅ 健康检查：`systemctl is-active`

### 手动触发

GitHub Actions → **Deploy to Oracle Cloud** → **Run workflow** → `main`

---

## 📊 监控部署

### 查看服务状态

```bash
ssh -i ~/.ssh/vedaaide_deploy opc@YOUR_ORACLE_IP

# 服务状态
sudo systemctl status vedaaide

# 实时日志
sudo journalctl -u vedaaide -f

# 最近 50 行日志
sudo journalctl -u vedaaide -n 50 --no-pager
```

---

## 🔄 环境变量配置

`.env` 文件位于 VM 的 `/home/opc/VedaAide/.env`。首次部署时由 GitHub Actions 自动写入 `DEEPSEEK_API_KEY` 和 `TELEGRAM_BOT_TOKEN`。其他变量可手动编辑：

```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN

# DeepSeek API
DEEPSEEK_API_KEY=YOUR_DEEPSEEK_API_KEY
DEEPSEEK_MODEL=deepseek-chat

# 数据库路径
DB_PATH=/home/opc/VedaAide/data/vedaaide.db

# 时区
TZ=Asia/Shanghai
```

**`.env` 文件被 rsync 和 git 均排除，不会被覆盖或泄露。**

---

## 🛠️ 故障排除

### SSH 连接失败

```bash
chmod 600 ~/.ssh/vedaaide_deploy
ssh -i ~/.ssh/vedaaide_deploy -v opc@YOUR_ORACLE_IP
```

### 服务启动失败

```bash
sudo journalctl -u vedaaide -n 50 --no-pager
```

### 手动重新部署

```bash
cd /home/opc/VedaAide
bash scripts/deploy.sh
```

---

## 📈 最佳实践

### 分支策略

```
main       ← 稳定生产分支（自动部署）
develop    ← 开发分支（本地测试）
feature/*  ← 功能分支（PR 后合并）
```

### 提交信息规范

```bash
git commit -m "feat: add record_event_skill"
git commit -m "fix: fix timeout issue"
git commit -m "docs: update deployment guide"
```

## 🔐 安全建议

- ✅ 定期轮换 SSH 密钥
- ✅ 定期审查 GitHub Secrets
- ✅ 不要将 .env 提交到 Git
- ✅ 使用 Oracle NSG 限制 VM 入站规则（只开 22 端口）

---

## 📞 常见问题

**Q: 部署失败会回滚吗？**
A: 不会自动回滚。`data/` 目录不受部署影响，数据安全。如需回滚代码，在本地 `git revert` 后重新 push。

**Q: .env 里的密钥会丢失吗？**
A: 不会。rsync 排除了 `.env`，deploy.yml 只在变量不存在时才追加写入，不会覆盖。

**Q: 如何跳过某次自动部署？**
A: 在提交信息中添加 `[skip ci]`：
```bash
git commit -m "docs: update README [skip ci]"
```

---

更新日期：2026-03-11
