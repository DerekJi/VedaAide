# 项目结构说明

```
VedaAide/
├── .github/
│   └── workflows/
│       ├── deploy.yml              # 自动部署到 Oracle Cloud（rsync + systemd）
│       └── ci.yml                  # CI 检查（代码质量、测试、安全）
│
├── .gitignore                       # Git 忽略列表
├── .env.example                     # 环境变量模板
├── package.json                     # 本地开发辅助脚本（npm run ...）
├── requirements.txt                 # 根级依赖（测试工具等）
├── test_mvp.py                      # 集成冒烟测试
├── README.md                        # 项目说明
├── STRUCTURE.md                     # 本文件：项目结构说明
│
├── docs/
│   ├── Issues_and_Progress.md       # ★ 问题清单与整改进度追踪
│   ├── CI_CD_Guide.md               # 完整 CI/CD 部署指南
│   ├── QuickStart_CI_CD.md          # 5 分钟快速部署
│   ├── Migration_Guide.md           # 数据迁移指南
│   └── DeepSeek极简策略.md          # 历史参考
│
├── bot_app/                         # ★ Bot 核心服务
│   ├── requirements.txt             # Bot 依赖（aiogram, aiosqlite, APScheduler 等）
│   ├── main.py                      # 主程序：Telegram Bot + 每日提醒调度器
│   ├── deepseek_client.py           # DeepSeek API 客户端（意图路由 + 信息提取）
│   ├── ollama_client.py             # Ollama 客户端（历史备用，不再使用）
│   ├── db_client.py                 # 数据库层：aiosqlite 直连 SQLite
│   ├── message_processor.py         # 业务逻辑层：纯函数，无 Telegram 依赖
│   └── skills/
│       ├── __init__.py              # 技能注册表和工厂
│       ├── base_skill.py            # Skill 基类
│       ├── record_event_skill.py    # 技能1：记录生活事件
│       └── schedule_event_skill.py  # 技能2：记录日程/周期事件
│
├── scripts/
│   ├── deploy.sh                    # VM 部署脚本（venv + systemd）
│   ├── vedaaide.service             # systemd service 文件
│   ├── setup_vm.sh                  # VM 首次初始化（只需执行一次）
│   ├── start_local.sh               # 本地开发一键启动
│   ├── restartable_bot_runner.py    # 本地开发：带自动重启的 Bot 运行器
│   └── view_db.mjs                  # 本地开发：直接读取 SQLite 查看数据
│
├── data/                            # SQLite 数据文件（Git 忽略）
│   └── vedaaide.db
│
├── tests/                           # ★ 自动化测试套件（pytest）
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_db_client.py
│   │   ├── test_message_processor_utils.py
│   │   └── test_skills.py
│   └── integration/
│       └── test_message_processor.py
│
└── logs/                            # 运行日志（Git 忽略）
```

---

## 架构说明

```
Telegram → aiogram (polling)
               ↓
        MessageProcessor
               ↓
        DeepSeek API  ←→  意图识别 / 实体提取
               ↓
           Skills
               ↓
          SQLite (aiosqlite)
```

---

## 环境变量

| 变量名 | 必填 | 说明 |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | Telegram Bot Token |
| `DEEPSEEK_API_KEY` | ✅ | DeepSeek API Key |
| `TELEGRAM_CHAT_ID` | 推荐 | 接收每日提醒的 chat ID |
| `DEEPSEEK_MODEL` | 可选 | 默认 `deepseek-chat` |
| `DB_PATH` | 可选 | SQLite 文件路径，默认 `./data/vedaaide.db` |
| `TZ` | 可选 | 时区，默认 `Asia/Shanghai` |
| `LOG_LEVEL` | 可选 | 日志级别，默认 `INFO` |

---

## 本地开发

```bash
cp .env.example .env
# 编辑 .env，填入 TELEGRAM_BOT_TOKEN 和 DEEPSEEK_API_KEY

npm start               # 启动 bot（带自动重启）
npm run db:view:events  # 查看生活事件
npm run db:view:schedules
npm run db:view:profile
```

## 部署流程

```
git push origin main
    ↓ GitHub Actions
    ├── rsync 推送源码到 VM
    └── SSH 执行 deploy.sh
          ├── pip install（venv）
          ├── systemctl restart vedaaide
          └── 健康检查
```

### 手动部署 / 排查

```bash
ssh -i ~/.ssh/vedaaide_deploy opc@YOUR_ORACLE_IP

sudo systemctl status vedaaide
sudo journalctl -u vedaaide -f
bash /home/opc/VedaAide/scripts/deploy.sh
```

---

## Git 工作流程推荐

1. **main 分支**: 生产分支（自动部署）
2. **develop 分支**: 开发分支
3. **feature/*** 分支**: 功能分支（从 develop 创建，PR 回 develop）
4. **hotfix/*** 分支**: 紧急修复（从 main 创建）

---

更新日期：2026-03-11
