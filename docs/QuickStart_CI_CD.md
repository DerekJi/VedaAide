# 🚀 快速启动：GitHub + Oracle Cloud 自动化部署

## 📋 部署架构

```
git push → GitHub Actions
  ├── rsync 推送源码到 VM（无需在 VM 安装 git）
  └── SSH 执行 deploy.sh
        ├── python3 -m venv venv
        ├── pip install -r requirements.txt
        └── systemctl restart vedaaide
```

VM 上**不需要安装任何软件**，python3 / venv / rsync 已预装在 Oracle Linux 9 中。

---

## 📋 5分钟快速设置

### 步骤 1：生成 SSH 密钥对（如果还没有）

```bash
ssh-keygen -t rsa -b 4096 -f ~/.ssh/vedaaide_deploy -N ""
cat ~/.ssh/vedaaide_deploy   # 复制私钥内容备用
```

### 步骤 2：初始化 Oracle VM

```bash
# 连接到 VM（Oracle Linux 默认用户是 opc，不是 ubuntu）
ssh -i ~/.ssh/vedaaide_deploy opc@YOUR_ORACLE_IP

# 在 VM 上执行（只需一次）
mkdir -p /home/opc/VedaAide/data /home/opc/VedaAide/logs
touch /home/opc/VedaAide/.env
```

### 步骤 3：在 GitHub 仓库添加 Secrets

**Settings → Secrets and variables → Actions → New repository secret**

| 名称 | 值 |
|------|-----|
| `ORACLE_SSH_PRIVATE_KEY` | `cat ~/.ssh/vedaaide_deploy` 的完整内容 |
| `ORACLE_SSH_USER` | `opc` |
| `ORACLE_SERVER_IP` | 你的 Oracle VM 公网 IP |
| `ORACLE_PROJECT_PATH` | `/home/opc/VedaAide` |
| `DEEPSEEK_API_KEY` | DeepSeek API Key |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token |

### 步骤 4：推送代码触发部署

```bash
git add .
git commit -m "chore: initial deployment"
git push origin main
```

打开 GitHub → **Actions** → 观察 **Deploy to Oracle Cloud** 运行日志。

---

## 🔍 验证部署成功

```bash
ssh -i ~/.ssh/vedaaide_deploy opc@YOUR_ORACLE_IP

# 查看服务状态
sudo systemctl status vedaaide

# 实时查看日志
sudo journalctl -u vedaaide -f
```

---

## ⚡ 常见用法

### 推送代码自动部署

```bash
git add .
git commit -m "feat: my change"
git push origin main
# 🚀 自动部署开始！
```

### 跳过自动部署

```bash
git commit -m "docs: minor fix [skip ci]"
```

### 手动触发部署

GitHub Actions → **Deploy to Oracle Cloud** → **Run workflow** → `main` 分支

---

## 🆘 快速故障排除

### SSH 连接失败

```bash
chmod 600 ~/.ssh/vedaaide_deploy
ssh -i ~/.ssh/vedaaide_deploy opc@YOUR_ORACLE_IP "echo 'Connection OK'"
# 如果失败，检查 Oracle 安全组是否放开了 22 端口
```

### 服务启动失败

```bash
ssh -i ~/.ssh/vedaaide_deploy opc@YOUR_ORACLE_IP
sudo journalctl -u vedaaide -n 50 --no-pager
```

### 手动重新部署

```bash
ssh -i ~/.ssh/vedaaide_deploy opc@YOUR_ORACLE_IP
cd /home/opc/VedaAide
bash scripts/deploy.sh
```

---

## 💡 提示

- **数据安全**：`data/` 目录在 rsync 和 git 中均被排除，不会被覆盖
- **.env 安全**：`.env` 被 rsync exclude，密钥仅从 GitHub Secrets 写入
- **监控**：可添加 Slack 通知（需配置 `SLACK_WEBHOOK_URL` Secret）

---

## 📚 了解更多

- 完整部署指南：[CI_CD_Guide.md](CI_CD_Guide.md)
- GitHub Actions 文档：https://docs.github.com/en/actions
- Docker Compose 参考：https://docs.docker.com/compose/compose-file/

---

🎉 **现在你的 VedaAide 已经拥有完整的 CI/CD 流程了！**

每次 push 到 `main` 分支，代码都会自动部署到 Oracle Cloud。
