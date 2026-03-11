# 项目结构说明

```
VedaAide/
├── .github/
│   └── workflows/
│       ├── deploy.yml              # 自动部署到Oracle Cloud的workflow
│       └── ci.yml                  # CI检查（代码质量、测试等）
│
├── .gitignore                       # Git 忽略列表
├── docker-compose.yml               # Docker Compose 完整配置
├── requirements.txt                 # Python 依赖
├── .env.example                     # 环境变量模板
│
├── docs/
│   ├── Architecture.md              # 核心设计文档（★重要）
│   ├── CI_CD_Guide.md               # 完整的 CI/CD 部署指南
│   ├── QuickStart_CI_CD.md          # 5分钟快速启动指南
│   ├── Migration_Guide.md           # 数据迁移指南
│   ├── SimpleArchitecture.md        # 历史参考（DeepSeek方案）
│   └── Gemini方案.md                # 历史参考（Gemini方案）
│
├── bot_app/
│   ├── Dockerfile                   # Bot服务的Docker镜像定义
│   ├── main.py                      # 主程序入口（待实现）
│   ├── requirements.txt              # Python依赖
│   │
│   └── skills/
│       ├── __init__.py
│       ├── base_skill.py            # Skill基类（待实现）
│       ├── record_event_skill.py    # 记录事件技能（待实现）
│       ├── schedule_event_skill.py  # 计划事件技能（待实现）
│       └── query_data_skill.py      # 数据查询技能（待实现）
│
├── sqlite_app/
│   ├── Dockerfile                   # SQLite Web API的Docker镜像
│   └── app.py                       # Flask Web API应用
│
├── scripts/
│   └── deploy.sh                    # Oracle Cloud 部署脚本
│
├── data/                            # SQLite 数据文件（Git忽略）
│   └── vedaaide.db
│
├── chroma_data/                     # ChromaDB 向量数据（Git忽略）
│
├── ollama_data/                     # Ollama 模型数据（Git忽略）
│
├── backups/                         # 自动备份目录（Git忽略）
│   ├── data_20260311_120000.tar.gz
│   ├── chroma_data_20260311_120000.tar.gz
│   └── deploy_20260311_120000.log
│
├── README.md                        # 项目概览（当前阅读）
└── .git/                            # Git 版本控制
```

---

## 核心文件说明

### .github/workflows/
- **deploy.yml**: GitHub Actions workflow，在 push 到 main 时自动触发部署
- **ci.yml**: 可选的代码质量检查、测试、安全检查等

### docs/
- **Architecture.md** - 必读！包含完整的架构设计和分阶段实施计划
- **QuickStart_CI_CD.md** - 5分钟快速启动 CI/CD
- **CI_CD_Guide.md** - 详细的部署指南

### bot_app/
Bot 核心服务代码，包含：
- main.py: Telegram Bot 主程序
- skills/: 各种功能技能模块

### sqlite_app/
SQLite 数据库的 Web API 服务，供其他容器访问

### scripts/
- deploy.sh: 在 Oracle VM 上执行的部署脚本，包含备份、健康检查等

---

## 开发工作流

### 第一次设置（本地开发）

```bash
# 克隆仓库
git clone https://github.com/YOUR_USERNAME/VedaAide.git
cd VedaAide

# 创建环境文件
cp .env.example .env
# 编辑 .env，添加你的 Telegram Token

# 启动本地开发环境
docker-compose up -d

# 查看日志
docker-compose logs -f core_service
```

### 开发流程

```bash
# 1. 创建功能分支
git checkout -b feature/my-new-skill

# 2. 开发和测试
# 编辑代码...
# 测试...

# 3. 提交代码
git add .
git commit -m "feat: implement new skill"
git push origin feature/my-new-skill

# 4. 创建 Pull Request
# GitHub 上创建 PR，等待 CI 检查通过

# 5. 合并到 main
# PR 审查通过后，点击 Merge
# 🚀 自动部署到 Oracle Cloud！
```

### 本地测试

```bash
# 启动所有服务
docker-compose up -d

# 查看容器状态
docker-compose ps

# 查看特定服务日志
docker-compose logs -f core_service

# 停止服务
docker-compose down

# 进入容器调试
docker exec -it vedaaide-core bash
```

---

## 部署流程

### 自动部署（推荐）

```
GitHub (main 分支)
    ↓ push
GitHub Actions (deploy.yml)
    ↓ checkout → SSH setup → deploy
Oracle Cloud VM (scripts/deploy.sh)
    ↓ git pull → backup → docker-compose up
✅ 完成
```

### 手动部署

```bash
# SSH 连接到 Oracle VM
ssh -i ~/.ssh/vedaaide_deploy ubuntu@YOUR_ORACLE_IP

# 进入项目目录
cd ~/VedaAide

# 手动运行部署脚本
bash scripts/deploy.sh
```

---

## 环境变量

**本地开发：**
- 复制 `.env.example` 为 `.env`
- 编辑 `.env` 添加本地配置

**生产环境（Oracle Cloud）：**
- 由部署脚本自动加载 `.env` 文件
- 确保 `.env` 在 `.gitignore` 中（不提交到 Git）

---

## 数据管理

### 数据位置

| 数据类型 | 位置 | 说明 |
|---------|------|------|
| 生活事件 | `data/vedaaide.db` | SQLite 数据库 |
| 向量记忆 | `chroma_data/` | ChromaDB（后期启用） |
| AI 模型 | `ollama_data/` | 本地 Ollama 模型 |
| 自动备份 | `backups/` | 每次部署前自动创建 |

### 备份恢复

```bash
# 停止容器
docker-compose down

# 恢复备份
tar -xzf backups/data_20260311_120000.tar.gz

# 重启
docker-compose up -d
```

---

## 常用命令

```bash
# 查看所有正在运行的容器
docker-compose ps

# 查看实时日志
docker-compose logs -f

# 进入容器交互式 shell
docker exec -it vedaaide-core bash

# 重启特定服务
docker-compose restart core_service

# 完全重建镜像
docker-compose build --no-cache

# 清理未使用的镜像和容器
docker image prune -f
docker container prune -f
```

---

## Git 工作流程推荐

1. **main 分支**: 生产分支（自动部署）
2. **develop 分支**: 开发分支
3. **feature/*** 分支**: 功能分支（从 develop 创建，PR 回 develop）
4. **hotfix/*** 分支**: 紧急修复（从 main 创建）

---

更新日期：2026-03-11
