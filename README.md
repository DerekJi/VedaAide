我想实现一个私人的这个助手，就是我日常生活里边的杂七杂八。

比方说我今天剪头了，今天去买菜了，家里还剩多少块肉，我看还有多少多少个饺子，还剩今天包了多少馄饨冻起来了。今天的肉馅用了多少，吃了几个人吃的，吃了多少个；孩子今天或者下礼拜要有什么活动，每个星期的星期一要游泳和Scouts、星期二/四有篮球训练，周四有音乐剧排练，星期六/日篮球比赛，等等。

学校也可能发邮件说两个学期后的什么时候，他们要出去Camping，时间有多久、要准备什么东西，我就发给系统，让它自己整理、保存。过两天呢，我看到邮件后又想起来了，觉得要补充带什么东西，再告诉系统，系统就能够找到这个事情，然后把要补充的内容智能化的添加进去。

我希望说给这个系统后，它就能记住。然后呢，比方说每天早上你就要提醒我，比如说今天孩子要游泳，那你就要提醒我说给孩子说，那孩子就要准备游泳包，今天要打篮球就要准备篮球包。今天那个放了学就得去游游泳，好，那那就得说啊，今也没时间做饭，就类似这种东西。它能每天给我生成提醒，然后每个周末也给我生成一个报告，然后下个星期的提醒，比如下星期孩子要去那个看病，你要准备什么什么东西。我希望它能做到这样。而且，孩子早上就要去学校了，它是不是得头天晚上给我个提醒，第二天早上孩子上学前也能收到个提醒。如果下周就要camping，这周就得提醒我，不然头灯啥的万一坏了呢，有的装备还没有呢，收到提醒我才好提前去买或者翻箱倒柜的找。

上面说的是事件和提醒的问题。

但还有类似背景知识和信息的部分。比如，小区收垃圾桶，黄桶和绿桶都是每两周收一次，这周收黄桶，下周就收绿桶。再比如，我家住在哪里，家里有什么人，健康状态、经济状态、家里环境等等，这些都不会导致直接的事件，但对某些事情就很重要，不然我说Marco的时候，它不知道是我儿子就不行。或者，我问：今天该推什么桶？或者，这周是黄桶还是绿桶？它得能理解我问的是什么，才可能回答正确。所以，它需要能接受这种背景信息/知识，自行创建类似Skills的文件或者数据库项目。


这是现在希望它能做的事情。

未来，我希望它能提供接口或者共享数据库什么的，以方便别的AI工具能在适当的时候，获取到必要的信息，这就能打通AI了。



### 1. 项目愿景 (Vision)

作为 Veda 家族的首个成员，**VedaAide** 定位于“非侵入式生活管家”，通过 Telegram 提供结构化数据管理与语义分析，彻底解决传统 AI 助手“Token 扫射”和“逻辑模糊”的问题。

### 2. 核心架构设计 (Architecture)

采用 **Docker Compose** 容器化部署，实现模块化解耦。**方案选定基于Gemini方案 + DeepSeek极简策略的混合方案**，优先数据隐私和成本控制：

| 组件名称 | 容器服务名 | 技术栈 | 职责 |
| --- | --- | --- | --- |
| **Bot 核心** | `vedaaide-core` | Python (aiogram) | 处理 TG 消息、Whisper 转录、技能分发 |
| **语义引擎** | `vedaaide-brain` | Ollama (LLaMA/Qwen) | 意图识别、实体提取、技能路由（完全本地，零成本） |
| **结构化库** | `vedaaide-db` | SQLite | 存储理发、库存、开销等**硬数据** |
| **记忆引擎** | `vedaaide-memory` | ChromaDB | 存储生活杂感、背景偏好等**软记忆**（后期扩展） |

---

## 📋 文档导航

| 文档 | 用途 |
|------|------|
| [Architecture.md](docs/Architecture.md) | **核心技术方案** - 完整的架构设计、分阶段实施计划 |
| [Migration_Guide.md](docs/Migration_Guide.md) | 数据迁移指南 - 从本地开发到云端生产 |
| [SimpleArchitecture.md](docs/SimpleArchitecture.md) | 历史参考 - DeepSeek 极简方案对比存档 |

---

## 🎯 技术选型决定

**方案：混合架构（Gemini 完整设计 + DeepSeek 极简策略）**

### 核心考虑

| 决策点 | 选择 | 原因 |
|------|------|------|
| 数据存储 | SQLite + ChromaDB（本地）| 完全隐私 + 数据自主控制 |
| AI 引擎 | Ollama + 开源模型（Qwen/LLaMA）| 免费 + 零成本长期运维 |
| 部署 | Docker Compose | 微服务解耦 + 易迁移 |
| 实施 | MVP 优先 | 2 周完成核心流程，快速验证 |

### 为什么不用 Gemini API/GPT-4o

- ❌ 持续付费（每月 token 成本）
- ❌ 数据隐私依赖第三方
- ❌ 延迟和配额限制
- ✅ Ollama 七参数量模型足以处理结构化任务

---

## 🔄 核心交互流程

VedaAide 采用**确认闭环设计**，确保每条数据都经过用户确认才入库，避免 LLM 理解偏差导致的数据污染。

```
用户发送文本
    ↓
Ollama 意图识别 (选择 Skill)
    ↓
Ollama 技能执行 (结构化提取)
    ↓
Bot 反馈给用户 (JSON + 确认按钮)
    ↓ [用户点击✅确认]
SQLite 持久化入库
```

**关键特性：**
- ✍️ **纯文字输入**：通过 Telegram 发送文本消息
- ✅ **确认必须**：无确认 = 无入库（防止误识别数据污染）
- 🧠 **本地处理**：所有识别在本地完成，零 API 调用
- 📊 **结构化存储**：确保数据清洁和可查询

详见 [Architecture.md](docs/Architecture.md) 的第4章。

---

## 💾 数据库结构

我们将 `data/` 目录映射至物理硬盘，确保持久化：

```sql
-- 生活事件记录表 (用于频率分析)
CREATE TABLE life_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    category TEXT, -- 'haircut', 'grocery', 'health'
    item TEXT,
    quantity REAL,
    unit TEXT,
    raw_text TEXT
);

-- 个人偏好隔离表 (解决“硬扯背景”问题)
CREATE TABLE user_profiles (
    key TEXT PRIMARY KEY,
    value TEXT,
    is_sensitive BOOLEAN DEFAULT 0 -- 敏感信息默认不主动读取
);

```

## 〰️ 完整技术文档

| 文档 | 内容 |
|------|------|
| [Architecture.md](docs/Architecture.md) | 核心设计、分阶段实施计划、Skill 架构 |
| [QuickStart_CI_CD.md](docs/QuickStart_CI_CD.md) | ⚡ **5分钟快速启动 CI/CD** |
| [CI_CD_Guide.md](docs/CI_CD_Guide.md) | 完整的 GitHub + Oracle Cloud 部署指南 |
| [Migration_Guide.md](docs/Migration_Guide.md) | 本地到生产环境的数据迁移 |

---

## 🔄 自动化部署（GitHub + Oracle Cloud）

**工作流程：** Push 代码 → GitHub Actions 自动部署 → Oracle VM 自动启动

### 快速 5 分钟设置

1. **生成 SSH 密钥**
   ```bash
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/vedaaide_deploy -N ""
   ```

2. **添加 4 个 GitHub Secrets**
   - `ORACLE_SSH_PRIVATE_KEY` - SSH 私钥
   - `ORACLE_SSH_USER` - SSH 用户名（ubuntu）
   - `ORACLE_SERVER_IP` - Oracle VM 公网 IP
   - `ORACLE_PROJECT_PATH` - 项目路径

3. **Push 代码自动部署**
   ```bash
   git push origin main
   ```

📖 详见 [QuickStart_CI_CD.md](docs/QuickStart_CI_CD.md)