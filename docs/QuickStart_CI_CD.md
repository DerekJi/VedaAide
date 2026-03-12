# 🚀 快速启动：GitHub + Oracle Cloud 自动化部署

## 📋 5分钟快速设置

### 步骤 1：生成 SSH 密钥对

**在本地机器运行：**

```bash
# 生成新的 SSH 密钥（无需密码）
ssh-keygen -t rsa -b 4096 -f ~/.ssh/vedaaide_deploy -N ""

# 输出私钥内容（待会要用）
cat ~/.ssh/vedaaide_deploy
```

### 步骤 2：配置 Oracle VM SSH 访问

**连接到 Oracle VM 并添加公钥：**

```bash
# 本地运行：上传公钥到 Oracle VM
ssh-copy-id -i ~/.ssh/vedaaide_deploy.pub ubuntu@YOUR_ORACLE_IP

# 或者手动添加：
ssh ubuntu@YOUR_ORACLE_IP << 'EOF'
mkdir -p ~/.ssh
cat >> ~/.ssh/authorized_keys << 'PUBKEY'
$(cat ~/.ssh/vedaaide_deploy.pub)
PUBKEY
chmod 600 ~/.ssh/authorized_keys
EOF
```

### 步骤 3：在 GitHub 仓库添加 Secrets

进入 GitHub 仓库：
1. **Settings** → **Secrets and variables** → **Actions**
2. 点击 **New repository secret**
3. 添加以下 4 个 Secrets：

| 名称 | 值 |
|------|-----|
| `ORACLE_SSH_PRIVATE_KEY` | 粘贴第 1 步的私钥内容（全部包括 `-----BEGIN-----` 和 `-----END-----`） |
| `ORACLE_SSH_USER` | `ubuntu` |
| `ORACLE_SERVER_IP` | 你的 Oracle VM 公网 IP |
| `ORACLE_PROJECT_PATH` | `/home/ubuntu/VedaAide` |

**示例：**

```
ORACLE_SSH_PRIVATE_KEY = 
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA1234567...
...（很多行）...
-----END RSA PRIVATE KEY-----
```

### 步骤 4：在 Oracle VM 准备项目

**SSH 连接到 Oracle VM：**

```bash
ssh -i ~/.ssh/vedaaide_deploy ubuntu@YOUR_ORACLE_IP

# 在 Oracle VM 上执行：
cd ~
git clone https://github.com/YOUR_USERNAME/VedaAide.git
cd VedaAide

# 创建 .env 文件（如果需要）
cat > .env << 'EOF'
TELEGRAM_BOT_TOKEN=your_telegram_token_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_MODEL=deepseek-chat
DB_PATH=/app/data/vedaaide.db
TZ=Asia/Shanghai
EOF

# 赋予部署脚本执行权限
chmod +x scripts/deploy.sh

# 首次手动启动（后续自动化）
docker-compose up -d
```

### 步骤 5：测试自动部署

**在本地 push 代码：**

```bash
git add .
git commit -m "test: trigger deployment"
git push origin main
```

**然后：**
1. 打开 GitHub → **Actions** 选项卡
2. 看到 **Deploy to Oracle Cloud** 工作流程运行中
3. 等待完成（通常 1-2 分钟）

---

## 🔍 验证部署成功

### 查看 GitHub Actions 日志

在 **Actions** 选项卡点击最新的 workflow 运行记录。

### SSH 到 Oracle VM 验证

```bash
ssh -i ~/.ssh/vedaaide_deploy ubuntu@YOUR_ORACLE_IP

cd ~/VedaAide

# 查看容器状态
docker-compose ps

# 查看最新日志
docker-compose logs -f vedaaide-bot

# 查看部署日志
tail -f backups/deploy_*.log
```

---

## ⚡ 常见用法

### 推送代码自动部署

```bash
# 修改代码
echo "# My change" >> README.md

# 提交并推送
git add README.md
git commit -m "docs: update README"
git push origin main

# 🚀 自动部署开始！
```

### 跳过自动部署

```bash
git commit -m "docs: minor fix [skip ci]"
```

### 手动触发部署

不 push 代码，直接在 GitHub Actions 中：
1. 选择 **Deploy to Oracle Cloud** workflow
2. 点击 **Run workflow** 
3. 选择 `main` 分支
4. 确认

---

## 🆘 快速故障排除

### 错误：SSH 连接失败

```bash
# 检查密钥权限（本地）
chmod 600 ~/.ssh/vedaaide_deploy

# 测试连接
ssh -i ~/.ssh/vedaaide_deploy ubuntu@YOUR_ORACLE_IP "echo 'Connection OK'"

# 如果失败，检查 Oracle 安全组规则是否允许 SSH（22 端口）
```

### 错误：找不到 docker-compose.yml

在 Oracle VM 上检查项目路径：

```bash
ssh ubuntu@YOUR_ORACLE_IP "ls -la ~/VedaAide/"
```

确保 `docker-compose.yml` 存在。

### 错误：容器启动失败

查看具体错误：

```bash
ssh ubuntu@YOUR_ORACLE_IP
cd ~/VedaAide
docker-compose logs -f
```

---

## 📊 观察部署进度

### 实时看日志

```bash
# GitHub Actions 中的日志（实时）
# Actions 选项卡 → Deploy to Oracle Cloud → Deploy to Oracle Cloud job

# Oracle VM 中的日志（实时）
ssh ubuntu@YOUR_ORACLE_IP "tail -f ~/VedaAide/backups/deploy_*.log"
```

### 检查容器状态

```bash
ssh ubuntu@YOUR_ORACLE_IP
cd ~/VedaAide
docker-compose ps
docker-compose logs -n 50 vedaaide-bot  # 最后 50 行日志
```

---

## 💡 提示

1. **数据安全**：每次部署前自动备份 `data/` 和 `chroma_data/` 目录
2. **零停机部署**：可选配置蓝绿部署（需进阶配置）
3. **监控**：可添加 Slack 通知（需配置 `SLACK_WEBHOOK_URL` Secret）
4. **版本管理**：使用 git tag 标记重要版本

---

## 📚 了解更多

- 完整部署指南：[CI_CD_Guide.md](CI_CD_Guide.md)
- GitHub Actions 文档：https://docs.github.com/en/actions
- Docker Compose 参考：https://docs.docker.com/compose/compose-file/

---

🎉 **现在你的 VedaAide 已经拥有完整的 CI/CD 流程了！**

每次 push 到 `main` 分支，代码都会自动部署到 Oracle Cloud。
