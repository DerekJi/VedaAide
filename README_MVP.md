# VedaAide - 个人生活助手机器人

![Status](https://img.shields.io/badge/status-MVP-brightgreen)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

> 一个隐私优先、本地运行的 Telegram 机器人，帮助您记住生活中的每一件事。

## ✨ 核心特性

### 🎯 MVP 功能（已实现）

- **📝 记录生活事件** - "今天剪头了" → 自动记录和分类
- **📅 规划日程事件** - "孩子每周二有游泳课" → 自动识别定期事件
- **✅ 智能确认** - 提取数据后显示确认界面，支持修改
- **🔒 完全隐私** - 所有数据存储在本地，Ollama 模型本地运行
- **🚀 开箱即用** - Docker Compose 一键启动

### 📈 后续规划

- **每日简报** - 早上提醒今天的日程
- **周报** - 总结本周发生的事情
- **搜索功能** - 快速查询历史事件
- **向量数据库** - 语义搜索和智能推荐
- **更多技能** - 库存管理、健康追踪、财务记录

## 📊 架构

```
┌─────────────────────────────────────────────────────────┐
│                 Telegram 用户                            │
└──────────────────────┬──────────────────────────────────┘
                       │ 消息
                       ↓
           ┌───────────────────────┐
           │   VedaAide Bot        │
           │  (aiogram 3.2.0)      │
           └──────────┬────────────┘
              ┌───────┴──────────┐
              ↓                  ↓
    ┌──────────────────┐  ┌──────────────────┐
    │ OllamaClient     │  │ DatabaseClient   │
    │ (skill routing)  │  │ (data storage)   │
    └────────┬─────────┘  └──────────┬────────┘
             │                       │
             ↓                       ↓
    ┌──────────────────┐  ┌──────────────────┐
    │  Ollama          │  │  SQLite          │
    │  qwen:7b-chat    │  │  + Flask API     │
    │  (LLM 推理)      │  │  (数据持久化)    │
    └──────────────────┘  └──────────────────┘
```

## 🚀 快速开始

### 前置条件

- Python 3.11+
- Docker & Docker Compose（推荐）
- Telegram Bot Token（从 [@BotFather](https://t.me/BotFather) 获取）

### 安装和启动

**方式 1：Docker Compose（推荐，一键启动）**

```bash
# 1. 克隆项目
git clone <repository>
cd VedaAide

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填写 TELEGRAM_BOT_TOKEN

# 3. 启动所有服务
docker-compose up -d

# 4. 查看日志
docker-compose logs -f vedaaide-bot

# 5. 测试（在 Telegram 中找到您的机器人，发送 /start）
```

**方式 2：本地开发**

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动 Ollama（需要单独安装，见下文）
ollama serve &

# 3. 拉取 LLM 模型（首次，~4GB）
ollama pull qwen:7b-chat

# 4. 启动数据库 API
python sqlite_app/app.py &

# 5. 启动机器人
python -m bot_app.main
```

## 📖 使用方法

### 在 Telegram 中与机器人交互

1. **启动机器人**
   ```
   /start
   ```

2. **记录生活事件**
   ```
   今天剪头了
   → 机器人: ✅ 识别成功
   → 类别: haircut
   → 物品: 理发
   → [✅ 确认入库] [❌ 重新识别]
   ```

3. **规划日程**
   ```
   孩子每周二有游泳课
   → 机器人: ✅ 识别成功
   → 标题: 游泳课
   → 时间: 2024-01-09T14:00:00
   → 重复规则: WEEKLY_TUE
   → [✅ 确认入库] [❌ 重新识别]
   ```

4. **查看帮助**
   ```
   /help
   ```

## 📁 项目结构

```
VedaAide/
├── bot_app/                           # 机器人核心代码
│   ├── main.py                        # 🤖 入口点
│   ├── ollama_client.py               # Ollama 通信
│   ├── db_client.py                   # 数据库通信
│   ├── Dockerfile                     # Docker 镜像
│   └── skills/
│       ├── base_skill.py              # 技能基类
│       ├── record_event_skill.py      # 记录事件技能
│       ├── schedule_event_skill.py    # 规划事件技能
│       └── __init__.py                # 技能注册
├── sqlite_app/
│   ├── app.py                         # SQLite Web API
│   └── Dockerfile
├── scripts/
│   ├── deploy.sh                      # 部署脚本
│   └── backup.sh                      # 备份脚本
├── .github/workflows/
│   └── deploy.yml                     # CI/CD 配置
├── docs/
│   ├── QuickStart_MVP.md              # MVP 快速开始
│   ├── MVP_Implementation.md          # 实现文档
│   ├── Architecture.md                # 完整设计文档
│   ├── Migration_Guide.md             # 迁移指南
│   └── QuickStart_CI_CD.md            # CI/CD 指南
├── docker-compose.yml                 # 容器编排
├── requirements.txt                   # Python 依赖
├── .env.example                       # 环境变量模板
├── test_mvp.py                        # 测试脚本
└── README.md                          # 本文件
```

## 🧪 测试 MVP

```bash
# 运行测试脚本（验证所有组件）
python test_mvp.py

# 预期输出：
# ✅ Ollama 客户端 - 测试技能路由
# ✅ 技能框架 - 测试 RecordEventSkill 和 ScheduleEventSkill
# ✅ 数据库客户端 - 测试数据保存
# ✅ 集成测试 - 完整流程测试
```

## 🔧 环境配置

### 创建 .env 文件

```bash
cp .env.example .env
```

### 填写必要的变量

```env
# Telegram Bot Token（必填）
TELEGRAM_BOT_TOKEN=your_token_here

# Ollama 服务地址（可选，默认 localhost:11434）
OLLAMA_BASE_URL=http://localhost:11434

# 数据库服务地址（可选，默认 localhost:5000）
DB_BASE_URL=http://localhost:5000

# 日志级别（可选，默认 INFO）
LOG_LEVEL=INFO
```

## 📊 API 端点

### 查询数据

```bash
# 获取所有生活事件
curl http://localhost:5000/api/life_events

# 按类别过滤
curl http://localhost:5000/api/life_events?category=haircut

# 获取所有计划事件
curl http://localhost:5000/api/scheduled_events

# 获取用户背景信息
curl http://localhost:5000/api/user_profile

# 健康检查
curl http://localhost:5000/health
```

## 🛠️ 故障排除

### 机器人不响应

```bash
# 1. 检查 Ollama 是否运行
curl http://localhost:11434/api/tags

# 2. 检查数据库 API 是否运行
curl http://localhost:5000/health

# 3. 查看机器人日志
docker-compose logs -f vedaaide-bot

# 4. 重启服务
docker-compose restart vedaaide-bot
```

### Ollama 响应超时

```bash
# 首次查询会比较慢（模型加载）
# 查看模型是否已加载
ollama list

# 如果没有，手动拉取
ollama pull qwen:7b-chat
```

### 数据库错误

```bash
# 检查 SQLite API 是否运行
curl http://localhost:5000/health

# 重启数据库服务
docker-compose restart vedaaide-db
```

## 📚 文档

| 文档 | 说明 |
|------|------|
| [QuickStart_MVP.md](./docs/QuickStart_MVP.md) | MVP 快速启动指南（5分钟） |
| [MVP_Implementation.md](./docs/MVP_Implementation.md) | 实现细节和架构 |
| [Architecture.md](./docs/Architecture.md) | 完整系统设计文档 |
| [QuickStart_CI_CD.md](./docs/QuickStart_CI_CD.md) | CI/CD 部署指南（Oracle Cloud） |
| [Migration_Guide.md](./docs/Migration_Guide.md) | 从作坊式到生产级别的迁移 |

## 🤝 开发

### 添加新技能

1. 在 `bot_app/skills/` 创建新文件：

```python
from bot_app.skills.base_skill import BaseSkill

class MyCustomSkill(BaseSkill):
    def get_name(self) -> str:
        return "my_custom_skill"
    
    def get_prompt(self, user_text: str) -> str:
        # 返回 Ollama Prompt
        return f"用户说: {user_text}\n请提取..."
    
    def parse_result(self, llm_output: str) -> dict:
        # 解析 LLM 输出
        return {...}
```

2. 在 `bot_app/skills/__init__.py` 注册：

```python
from bot_app.skills.my_custom_skill import MyCustomSkill

SKILLS = {
    "my_custom_skill": MyCustomSkill,
    ...
}
```

### 运行本地开发版本

```bash
# 安装依赖
pip install -r requirements.txt

# 启动各个服务
ollama serve &
python sqlite_app/app.py &
python -m bot_app.main
```

## 📞 技术栈

| 组件 | 技术 | 版本 |
|------|------|------|
| 机器人框架 | aiogram | 3.2.0 |
| LLM 引擎 | Ollama | latest |
| LLM 模型 | Qwen 7B Chat | - |
| 数据库 | SQLite | 3.x |
| 数据库 API | Flask | 3.0.0 |
| HTTP 客户端 | httpx | 0.25.0 |
| 运行时 | Python | 3.11+ |
| 容器 | Docker | latest |
| 编排 | Docker Compose | latest |
| CI/CD | GitHub Actions | - |

## 🔐 隐私与安全

- ✅ **本地优先** - 所有数据存储在本地 SQLite，不上传到云端
- ✅ **开源模型** - 使用开源的 Ollama + Qwen，完全可控
- ✅ **离线运行** - 除了 Ollama 模型初始化，其他都可离线运行
- ✅ **完全控制** - 您掌握所有数据，随时可以导出或删除

## 📈 性能指标

| 操作 | 时间 | 说明 |
|------|------|------|
| 首次启动模型 | ~10s | 模型首次加载到内存 |
| 技能识别 | ~2-5s | 调用 Ollama 识别用户意图 |
| 数据提取 | ~3-8s | 执行技能提取结构化数据 |
| 数据保存 | <100ms | 保存到本地数据库 |
| 总响应时间 | ~5-15s | 从接收消息到确认界面显示 |

## 🚀 部署

### Oracle Cloud（免费 VM）

```bash
# 详见 docs/QuickStart_CI_CD.md

# 核心步骤：
# 1. 在 GitHub 设置 Secrets
# 2. 推送到 main 分支
# 3. GitHub Actions 自动部署到 Oracle Cloud
```

### 本地 VPS

```bash
# SSH 登录到服务器
ssh user@your-server

# 克隆项目
git clone <repository>
cd VedaAide

# 配置环境变量
nano .env

# 启动
docker-compose up -d
```

## 📝 更新日志

### v1.0.0 (MVP)
- ✅ 记录生活事件功能
- ✅ 规划日程事件功能
- ✅ Telegram 机器人交互
- ✅ SQLite 数据存储
- ✅ Ollama 本地 LLM
- ✅ Docker 容器化
- ✅ GitHub Actions CI/CD

## 🎯 下一步

1. **完成 MVP 测试**
   - [ ] 本地测试所有功能
   - [ ] 在 Telegram 中与机器人交互
   - [ ] 验证数据正确保存

2. **部署到云端**
   - [ ] 配置 GitHub Secrets
   - [ ] 推送到 GitHub
   - [ ] 部署到 Oracle Cloud

3. **收集反馈并迭代**
   - [ ] 使用过程中记录问题
   - [ ] 优化 Prompt 提高识别率
   - [ ] 添加用户反馈的新功能

## ❓ 常见问题

**Q: 需要购买任何服务吗？**
A: 不需要。Ollama 和 SQLite 都是免费开源的。Oracle Cloud 提供免费 VM。唯一的成本是 Telegram Bot（完全免费）。

**Q: 可以用其他 LLM 模型吗？**
A: 可以。Ollama 支持许多模型（Llama 2, Mistral, 等）。编辑 `docker-compose.yml` 中的 `OLLAMA_MODEL` 即可。

**Q: 如何添加新的技能？**
A: 详见本 README 的"开发"部分。核心是继承 `BaseSkill` 并实现三个方法。

**Q: 数据会丢失吗？**
A: SQLite 的数据持久化在 `./data` 目录。Docker Compose 配置了 volume，数据在容器删除后仍然保留。建议定期备份。

## 📜 许可证

MIT License - 详见 [LICENSE](LICENSE)

## 🙏 致谢

- [Ollama](https://ollama.ai/) - 本地 LLM 推理引擎
- [Aiogram](https://docs.aiogram.dev/) - Python Telegram Bot 框架
- [Qwen](https://huggingface.co/Qwen) - 开源 LLM 模型

---

**准备好了吗？** 👉 [快速开始 5 分钟](./docs/QuickStart_MVP.md)

如有问题，欢迎提交 Issue 或 PR！ 🚀

