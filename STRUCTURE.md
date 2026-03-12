# 项目结构说明

```
VedaAide/
├── .github/
│   └── workflows/
│       ├── deploy.yml              # 自动部署到Oracle Cloud的workflow
│       └── ci.yml                  # CI检查（代码质量、测试等）
│
├── .gitignore                       # Git 忽略列表
├── .env.example                     # 环境变量模板
├── docker-compose.yml               # Docker Compose 配置（核心服务：bot + ollama）
├── package.json                     # 本地开发辅助脚本（npm run ...）
├── requirements.txt                 # 根级依赖（含 Flask，仅本地开发工具使用）
├── test_mvp.py                      # MVP 功能集成测试脚本
├── README.md                        # 项目愿景与需求说明
├── README_MVP.md                    # MVP 快速启动文档
├── STRUCTURE.md                     # 本文件：项目结构说明
│
├── docs/
│   ├── Issues_and_Progress.md       # ★ 问题清单与整改进度追踪（重要）
│   ├── Test_Plan.md                 # ★ 测试方案（不依赖具体实现，覆盖所有核心需求）
│   ├── MVP_Implementation.md        # 历史参考：MVP 实现总结
│   ├── QuickStart_MVP.md            # 快速启动指南（MVP）
│   ├── CI_CD_Guide.md               # 完整的 CI/CD 部署指南
│   ├── QuickStart_CI_CD.md          # 5分钟快速启动 CI/CD
│   ├── Migration_Guide.md           # 数据迁移指南
│   ├── DeepSeek极简策略.md          # 历史参考（DeepSeek方案）
│   └── Gemini方案.md                # 历史参考（Gemini方案）
│
├── bot_app/                         # ★ Bot 核心服务
│   ├── Dockerfile                   # Bot 服务的 Docker 镜像定义
│   ├── requirements.txt             # Bot 依赖（aiogram, aiosqlite, APScheduler 等）
│   ├── main.py                      # 🤖 主程序入口：Telegram Bot + 每日提醒调度器
│   ├── ollama_client.py             # LLM 通信：与 Ollama 交互（意图路由 + 信息提取）
│   ├── db_client.py                 # 数据库层：直接通过 aiosqlite 操作 SQLite
│   ├── message_processor.py         # 业务逻辑层：纯函数，无 Telegram 依赖，供测试共用
│   └── skills/
│       ├── __init__.py              # 技能注册表和工厂
│       ├── base_skill.py            # Skill 基类（抽象接口）
│       ├── record_event_skill.py    # 技能1：记录一次性生活事件
│       └── schedule_event_skill.py  # 技能2：记录计划/周期性事件
│
├── sqlite_app/                      # 本地开发工具：SQLite Web API
│   ├── Dockerfile                   # 仅用于 --profile tools 启动
│   └── app.py                       # Flask Web API（供 view_db.mjs 等脚本使用）
│
├── scripts/
│   ├── deploy.sh                    # Oracle Cloud 部署脚本
│   ├── start_local.sh               # 本地开发一键启动脚本
│   ├── restartable_bot_runner.py    # 本地开发带自动重启的 Bot 运行器
│   └── view_db.mjs                  # 本地开发：通过 Flask API 查看数据库内容
│
├── data/                            # SQLite 数据文件（Git忽略）
│   └── vedaaide.db
│
├── tests/                           # ★ 自动化测试套件（pytest + pytest-asyncio）
│   ├── conftest.py                  # 共享 fixtures（event_loop, tmp_db）
│   ├── unit/
│   │   ├── test_db_client.py        # DB 层单元测试（13 个用例）
│   │   ├── test_message_processor_utils.py  # 纯函数单元测试（27 个用例）
│   │   └── test_skills.py           # RecordEventSkill / ScheduleEventSkill 解析测试（21 个用例）
│   └── integration/
│       └── test_message_processor.py  # MessageProcessor 端到端集成测试（18 个用例）
│
├── ollama_data/                     # Ollama 模型数据（Git忽略）
│
├── chroma_data/                     # ChromaDB 向量数据（后期，Git忽略）
│
├── logs/                            # 运行日志（Git忽略）
│
└── .git/                            # Git 版本控制
```

---

## 架构说明

### 核心服务依赖关系（生产）

```
Bot（vedaaide-bot）
  ├── 直连 SQLite 文件（via aiosqlite，无 HTTP 层）
  └── HTTP → Ollama（LLM 推理）
```

**不再依赖 Flask**。Flask + vedaaide-db 容器已改为本地开发工具，通过 `--profile tools` 启动。

### 本地开发工具

```bash
# 启动 Flask API（用于 view_db 等脚本）
docker-compose --profile tools up -d vedaaide-db

# 查看数据库内容
npm run db:view:events
npm run db:view:schedules
npm run db:view:profile
```

---

## 环境变量

| 变量名 | 必填 | 说明 |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | 推荐 | 接收每日提醒的 chat ID（不设则跳过推送）|
| `OLLAMA_URL` | 可选 | Ollama 服务地址，默认 `http://localhost:11434` |
| `OLLAMA_MODEL` | 可选 | 使用的 LLM 模型，默认 `qwen:7b-chat` |
| `DB_PATH` | 可选 | SQLite 文件路径，默认 `./data/vedaaide.db` |
| `TZ` | 可选 | 时区，默认 `Asia/Shanghai` |
| `LOG_LEVEL` | 可选 | 日志级别，默认 `INFO` |

---

## 开发工作流

### 本地开发

```bash
# 方式1：Docker Compose（推荐）
docker-compose up -d  # 启动 bot + ollama

# 方式2：手动
npm run start:local      # 启动 Ollama + Flask + Bot
npm run bot:watch        # 带自动重启的 Bot
npm run test:mvp         # 运行集成测试
```

### 数据查看

```bash
# 需要先启动 Flask 服务工具
docker-compose --profile tools up -d vedaaide-db
# 或本地: npm run db:local

npm run db:view:events    # 查看生活事件
npm run db:view:schedules # 查看计划事件
npm run db:view:profile   # 查看背景信息
```

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
