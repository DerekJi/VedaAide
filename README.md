我想实现一个私人的这个助手，就是我日常生活里边的杂七杂八。

比方说我今天剪头了，今天去买菜了，家里还剩多少块肉，我看还有多少多少个饺子，还剩今天包了多少馄饨冻起来了。今天的肉馅用了多少，吃了几个人吃的，吃了多少个；孩子今天或者下礼拜要有什么活动，每个星期的星期一要游泳和Scouts、星期二/四有篮球训练，周四有音乐剧排练，星期六/日篮球比赛，等等。

学校也可能发邮件说两个学期后的什么时候，他们要出去Camping，时间有多久、要准备什么东西，我就发给系统，让它自己整理、保存。过两天呢，我看到邮件后又想起来了，觉得要补充带什么东西，再告诉系统，系统就能够找到这个事情，然后把要补充的内容智能化的添加进去。

我希望说给这个系统后，它就能记住。然后呢，比方说每天早上你就要提醒我，比如说今天孩子要游泳，那你就要提醒我说给孩子说，那孩子就要准备游泳包，今天要打篮球就要准备篮球包。今天那个放了学就得去游游泳，好，那那就得说啊，今也没时间做饭，就类似这种东西。它能每天给我生成提醒，然后每个周末也给我生成一个报告，然后下个星期的提醒，比如下星期孩子要去那个看病，你要准备什么什么东西。我希望它能做到这样。而且，孩子早上就要去学校了，它是不是得头天晚上给我个提醒，第二天早上孩子上学前也能收到个提醒。如果下周就要camping，这周就得提醒我，不然头灯啥的万一坏了呢，有的装备还没有呢，收到提醒我才好提前去买或者翻箱倒柜的找。

上面说的是事件和提醒的问题。

但还有类似背景知识和信息的部分。比如，小区收垃圾桶，黄桶和绿桶都是每两周收一次，这周收黄桶，下周就收绿桶。再比如，我家住在哪里，家里有什么人，健康状态、经济状态、家里环境等等，这些都不会导致直接的事件，但对某些事情就很重要，不然我说Marco的时候，它不知道是我儿子就不行。或者，我问：今天该推什么桶？或者，这周是黄桶还是绿桶？它得能理解我问的是什么，才可能回答正确。所以，它需要能接受这种背景信息/知识，自行创建类似Skills的文件或者数据库项目。


还有一类需求，是我自己都没意识到的规律。比如，今天换了牙刷头，三个月后又换了一次。我自己并没有主动告诉系统"我每三个月换一次牙刷头"，但系统应该能从历史记录里自己总结出来：这类事情有一定规律，大约每隔三个月发生一次。然后，如果我问"是不是该换牙刷头了？"，它就能根据自动发现的规律来回答。更好的情况是，还能把这条推断出来的规律写进背景信息里，下次直接用，不用每次都重新分析全量数据。至于什么时候做这个分析——等我主动问的时候再做（按需）、还是在每周定时提醒里顺带批量做（定时）——两种策略各有成本取舍，待实现时根据LLM实际消耗来决定。

这是现在希望它能做的事情。

未来，我希望它能提供接口或者共享数据库什么的，以方便别的AI工具能在适当的时候，获取到必要的信息，这就能打通AI了。



### 1. 项目愿景 (Vision)

作为 Veda 家族的首个成员，**VedaAide** 定位于“非侵入式生活管家”，通过 Telegram 提供结构化数据管理与语义分析，彻底解决传统 AI 助手“Token 扫射”和“逻辑模糊”的问题。

### 2. 核心架构设计 (Architecture)

直接部署在 Oracle Cloud VM 上（无容器），systemd 管理进程。

| 组件 | 技术栈 | 职责 |
| --- | --- | --- |
| **Bot 核心** | Python / aiogram | 处理 Telegram 消息、技能分发、FSM 多轮对话 |
| **AI 引擎** | DeepSeek API | 意图识别、实体提取、技能路由 |
| **结构化库** | SQLite（aiosqlite）| 存储生活事件、日程、背景信息等硬数据 |
| **软记忆引擎** | ChromaDB | 存储生活杂感、背景偏好等软记忆（**后期规划，暂未实现**） |

---

## 📋 文档导航

| 文档 | 用途 |
|------|------|
| [QuickStart_CI_CD.md](docs/QuickStart_CI_CD.md) | 5 分钟快速部署到 Oracle Cloud |
| [CI_CD_Guide.md](docs/CI_CD_Guide.md) | 完整 CI/CD 部署指南 |
| [Migration_Guide.md](docs/Migration_Guide.md) | 数据迁移指南 |

---

## 🎯 技术选型决定

### 核心考虑

| 决策点 | 当前选择 | 原因 |
|------|------|------|
| 数据存储 | SQLite（本地文件）| 完全隐私 + 零成本 + 数据自主控制 |
| AI 引擎 | DeepSeek API | 成本极低 + 推理能力强 |
| 部署 | Oracle Cloud Always Free VM + systemd | 永久免费 + 简单可靠 |
| 实施 | MVP 优先 | 快速启动，按需扩展 |

### 为什么不用 Gemini API/GPT-4o

- ❌ 持续付费（每月 token 成本高）
- ❌ 数据隐私依赖第三方
- ✅ DeepSeek API 成本极低，结构化任务表现强

---

## 🔄 核心交互流程

VedaAide 采用**确认闭环设计**，确保每条数据都经过用户确认才入库。

```
用户发送文本
    ↓
DeepSeek API 意图识别（选择 Skill）
    ↓
DeepSeek API 技能执行（结构化提取）
    ↓
Bot 反馈给用户（提取结果 + 确认按钮）
    ↓ [用户点击 ✅ 确认]
SQLite 持久化入库
```

**关键特性：**
- ✍️ **纯文字输入**：通过 Telegram 发送文本消息
- ✅ **确认必须**：无确认 = 无入库（防止误识别数据污染）
- 🔒 **数据自主**：SQLite 文件存在自己的服务器，完全隐私
- 📊 **结构化存储**：确保数据清洁和可查询

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
   - `ORACLE_SSH_USER` - SSH 用户名（`opc`，Oracle Linux 默认用户）
   - `ORACLE_SERVER_IP` - Oracle VM 公网 IP
   - `ORACLE_PROJECT_PATH` - 项目路径

3. **Push 代码自动部署**
   ```bash
   git push origin main
   ```

📖 详见 [QuickStart_CI_CD.md](docs/QuickStart_CI_CD.md)