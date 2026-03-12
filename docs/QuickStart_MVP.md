# VedaAide MVP 快速启动指南

## 📋 前置条件

- **Python**: 3.11+
- **Docker**: 用于运行 Ollama（推荐）或本地 Python 环境
- **Telegram Bot Token**: 从 [@BotFather](https://t.me/BotFather) 获取

## 🚀 快速启动（5分钟）

### 1️⃣ 获取 Telegram Bot Token

1. 在 Telegram 中搜索 `@BotFather`
2. 发送 `/newbot` 命令
3. 按提示输入机器人名称和用户名
4. 复制收到的 Token（格式类似：`123456:ABC-DEF...`）

### 2️⃣ 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填写：
# TELEGRAM_BOT_TOKEN=your_token_here
```

### 3️⃣ 启动依赖服务

#### 选项 A：使用 Docker Compose（推荐）

```bash
# 启动所有服务：Ollama + SQLite Web API + Bot
docker-compose up -d

# 查看日志
docker-compose logs -f vedaaide-bot
```

#### 选项 B：手动启动

**启动 Ollama**：
```bash
# macOS/Linux
ollama serve

# Windows - 下载安装程序：https://ollama.ai/download
# 然后运行
ollama serve
```

**拉取 LLM 模型**（首次，~4GB）：
```bash
ollama pull qwen:7b-chat
```

**启动 SQLite Web API**：
```bash
python sqlite_app/app.py
# 访问 http://localhost:5000/api/life_events
```

**启动 Bot**：
```bash
# 安装依赖
pip install -r requirements.txt

# 运行机器人
python -m bot_app.main
```

### 4️⃣ 测试机器人

1. 在 Telegram 中搜索您创建的机器人
2. 发送 `/start` 命令
3. 发送测试消息：
   - "今天剪头了" → 记录生活事件
   - "孩子每周二有游泳课" → 记录计划事件

## 🔍 架构和工作流程

### 消息处理流程

```
用户消息
  ↓
[OllamaClient.skill_router()]
  选择合适的技能（RecordEvent / ScheduleEvent）
  ↓
[Skill.execute()]
  调用 Ollama 提取结构化数据
  ↓
[主程序显示确认界面]
  展示提取的数据，等待用户确认
  ↓
用户点击 ✅ 或 ❌
  ✅ 确认 → DatabaseClient.create_*() → SQLite
  ❌ 拒绝 → 清除状态，等待重新输入
```

### 技能清单（Phase 1）

| 技能 | 用途 | 例子 |
|------|------|------|
| `record_event` | 记录一次性事件 | "今天剪头了"、"买了面包" |
| `schedule_event` | 规划定期/未来事件 | "周二有游泳课"、"明天看医生" |

## 🛠️ 文件结构

```
VedaAide/
├── bot_app/
│   ├── main.py                 # 🤖 机器人主程序
│   ├── ollama_client.py        # Ollama 通信客户端
│   ├── db_client.py            # 数据库通信客户端
│   └── skills/
│       ├── base_skill.py       # 技能基类
│       ├── record_event_skill.py
│       ├── schedule_event_skill.py
│       └── __init__.py         # 技能注册表
├── sqlite_app/
│   └── app.py                  # SQLite Web API 服务
├── docker-compose.yml          # Docker 编排配置
├── requirements.txt            # Python 依赖
├── .env.example                # 环境变量模板
└── docs/
    └── Architecture.md         # 完整架构设计
```

## 🐛 故障排查

### 问题：机器人不响应

**检查列表**：
1. Telegram Bot Token 是否正确？
2. Ollama 服务是否运行？
   ```bash
   curl http://localhost:11434/api/tags
   ```
3. SQLite Web API 是否运行？
   ```bash
   curl http://localhost:5000/health
   ```
4. 查看日志：
   ```bash
   docker-compose logs vedaaide-bot
   ```

### 问题：命令超时（Ollama 响应慢）

- 首次查询会比较慢（模型加载）
- 检查模型是否加载：`ollama list`
- 如果没有，手动拉取：`ollama pull qwen:7b-chat`

### 问题：数据库错误

- 检查 SQLite API 是否运行：`curl http://localhost:5000/health`
- 查看数据库日志：`docker-compose logs vedaaide-sqlite-api`
- 手动重启：`docker-compose restart vedaaide-sqlite-api`

## 📊 监控

### 查看数据

通过 SQLite Web API：

```bash
# 查看所有生活事件
curl http://localhost:5000/api/life_events

# 查看所有计划事件
curl http://localhost:5000/api/scheduled_events

# 查看用户背景信息
curl http://localhost:5000/api/user_profile
```

### 查看机器人日志

```bash
docker-compose logs -f vedaaide-bot

# 或者本地运行时：
# 运行 main.py，日志会直接输出到控制台
```

## 🔄 下一步（Phase 2）

- [ ] 每日简报（Daily Briefing）
- [ ] 周报（Weekly Summary）
- [ ] 搜索功能（查询历史事件）
- [ ] 向量数据库（ChromaDB 语义搜索）
- [ ] 背景信息管理

## 💡 开发提示

### 添加新技能

1. 在 `bot_app/skills/` 中创建新文件：`my_skill.py`
2. 继承 `BaseSkill`
3. 实现 `get_name()`、`get_prompt()`、`parse_result()` 方法
4. 在 `bot_app/skills/__init__.py` 中注册

### 修改 Ollama 模型

编辑 `docker-compose.yml`：

```yaml
ollama:
  environment:
    - OLLAMA_MODEL=qwen:14b-chat  # 改为其他模型
```

然后重启：
```bash
docker-compose restart ollama
```

## 📞 技术栈

| 组件 | 技术 | 版本 |
|------|------|------|
| 机器人框架 | aiogram | 3.2.0 |
| LLM 引擎 | Ollama | latest |
| 数据库 | SQLite | 3.x |
| 数据库 API | Flask | 3.0.0 |
| HTTP 客户端 | httpx | 0.25.0 |
| 容器化 | Docker Compose | latest |

## ✅ 验证清单

运行以下命令验证 MVP 完整工作：

```bash
# 1. 所有服务启动
docker-compose ps

# 2. Ollama 就绪
curl -s http://localhost:11434/api/tags | grep qwen

# 3. 数据库 API 就绪
curl -s http://localhost:5000/health

# 4. 机器人日志无错误
docker-compose logs vedaaide-bot | grep ERROR

# 5. 向机器人发送测试消息
# 在 Telegram 中发送 "今天剪头了"
# 应该看到确认对话框
```

---

✨ **祝您使用愉快！** 有问题？查看 [完整架构文档](./Architecture.md)
