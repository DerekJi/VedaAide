## 1. 项目目标

* **精准记录：** 通过 Telegram 语音/文字记录日常生活琐事，例如理发、库存（剩几块肉、多少馄饨）、开销、**孩子每周的固定活动与临时安排**，以及**完成这些活动需要做的准备**。
* **智能分析：** 自动分析重复事件的频率（如：理发周期、食物消耗速度）。
* **零干扰记忆：** 彻底隔离家庭背景信息，除非主动问起，否则 AI 不会“闲聊”家人情况。
* **主动提醒：** **每日清晨**推送当日总览（如：提醒为孩子的游泳课准备泳具包），并结合库存分析，定时推送理发提醒或**生成周度总结与下周计划**。

---

## 2. 方案选定背景

本架构设计综合了**Gemini 完整方案** 和 **DeepSeek 极简策略**：

| 决策点 | 选择 | 原因 |
|------|------|------|
| **AI模型** | **Ollama本地部署** | ✅ 完全隐私 + 长期零成本，不依赖外部API |
| **部署方式** | **Docker Compose** | ✅ 完整的微服务体系 + 数据完全自主 |
| **初期目标** | **MVP极简优先** | ✅ 先验证核心"识别→确认→入库"流程，避免过度设计 |
| **成本** | **Oracle 免费实例** | ✅ 4C/24G ARM + 引导卷足以运行 |

---

## 3. 技术方案架构

我们将采用 **Docker Compose** 在云端（推荐 Oracle Cloud）部署四套核心组件：

### A. 接入层 (Gateway)

* **输入渠道：** Telegram Bot 作为唯一入口，负责接收用户的文本消息。
* **消息处理：** Bot 接收用户文本后，**立即将其发送给"语义大脑 (Brain Engine)"进行意图分析**。根据大脑返回的结果，向用户反馈结构化数据，并请求用户确认（通过 Inline Buttons）。

### B. 语义大脑与存储层 (Brain & Storage)

1. **技能驱动的大脑 (Skill-Based Brain Engine):**
* **技术核心:** **本地部署 Ollama** 运行开源大语言模型 (LLM)。
* **推荐模型:** `qwen:7b-chat` (通义千问) 或 `llama3:8b-instruct`。这些模型在您的 Oracle ARM (4C/24G) 服务器上能以不错的性能运行，且完全免费。
* **核心架构: 两阶段执行模式**
    1.  **技能调度器 (Skill Router):**
        *   **职责:** 这是第一层 LLM 调用。它的唯一任务是分析用户输入，并从一个预定义的技能列表中选择最匹配的一个。
        *   **输入:** 用户的原始文本，例如“提醒我下周二带孩子去游泳”。
        *   **输出:** 一个技能名称，例如 `schedule_event`。
    2.  **技能执行器 (Skill Executor):**
        *   **职责:** 这是第二层 LLM 调用。`core_service` 根据调度器返回的技能名称，加载对应的技能模块。每个技能模块都有自己**高度优化和专用**的 Prompt。
        *   **示例:**
            *   `record_event_skill`: 它的 Prompt 专注于从文本中提取 `(item, quantity, unit)` 等实体。
            *   `schedule_event_skill`: 它的 Prompt 专注于提取 `(title, start_time, recurrence_rule)` 等实体。
            *   `query_data_skill`: 它的 Prompt 专注于将自然语言问题转化为精确的 SQL 查询。
* **优势:**
    *   **模块化:** 每个技能都是一个独立的单元（例如一个 Python 文件），可以独立开发、测试和优化。
    *   **高精度:** 每个技能的 Prompt 都很简短、专注，大大提高了 LLM 理解和执行任务的准确性。
    *   **可扩展性:** 增加新功能（例如“天气查询技能”）只需要新增一个技能文件，而无需修改任何现有逻辑。

2. **SQLite (结构化数据库)：** 存储“硬指标”。
* *表 `life_events`：* `(event_date, category, item, quantity, unit, notes)`
* *用途：* 记录已发生的**一次性事件**，如购物、理发、烹饪消耗、某天吃了几个饺子等。

3. **`scheduled_events` 表 (同样在 SQLite)：**
* *表 `scheduled_events`：* `(id, title, category, start_time, recurrence_rule, required_items, notes)`
* *用途：* 专门存储**未来或周期性事件**。例如孩子的游泳课（每周二）、篮球课、医生预约等。`recurrence_rule` 用于定义重复规则（例如 `'WEEKLY_TUE'`），`required_items` 用于生成准备提醒（例如 `'游泳包, 泳镜'`)。这正是实现您孩子日程管理和提醒的关键。

4. **ChromaDB (向量数据库)：** 存储“软记忆”。
* *用途：* 随手记的想法、复杂的事情描述、个人偏好。

### C. 部署环境 (Environment)

* **平台：** Oracle Cloud (ARM 4C/24G 免费实例)。
* **持久化：** Docker Volume 映射至引导卷，确保重启不丢数据。

---

## 3. 分阶段实施计划

本项目采用**MVP优先策略**，分三个阶段逐步完成，降低初期复杂度，快速验证核心流程：

### 阶段一：极简MVP（第1-2周）⭐

**目标：** 验证"语音→识别→确认→入库"的闭环

**实现范围：**
- ✅ Telegram Bot 文本输入接收
- ✅ Ollama 本地意图识别与实体提取（仅 `record_event_skill` + `schedule_event_skill`）
- ✅ SQLite 数据持久化
- ✅ 用户确认的 Inline Buttons 交互

**不包括：**
- ❌ ChromaDB（后期加入）
- ❌ 定时任务/提醒
- ❌ 复杂的 Skill（如频率分析、周报生成）

### 阶段二：添加提醒能力（第3-4周）

**实现范围：**
- ✅ Cron 定时任务
- ✅ 每日简报 (Daily Briefing)
- ✅ 更多 Skill（`query_data_skill`, `garbage_bin_skill`）
- ✅ 周报生成

### 阶段三：完整功能（第5周+）

- ✅ ChromaDB 软记忆集成
- ✅ 邮件/截图输入支持
- ✅ 更多高级 Skill
- ✅ 前端仪表板

---

## 4. 核心功能实现逻辑

### 第一阶段：文字入库确认流

1. **用户：** 发送文本"今天剪头了"。
2. **技能调度 (第一层调用):**
    *   `core_service` 将文本"今天剪头了"发送给 Ollama，使用**调度器 Prompt**。
    *   Ollama 返回最匹配的技能名称：`"record_event"`。
3. **技能执行 (第二层调用):**
    *   `core_service` 加载 `record_event_skill` 模块。
    *   该模块使用自己**专用的 Prompt** 和文本"今天剪头了"再次调用 Ollama。
    *   Ollama 返回精确的结构化数据：`{category: "haircut", item: "haircut", quantity: 1, notes: "今天剪头了"}`。
4. **Bot 回复：** "已识别：记录了一次理发。✅确认 / ❌修改"
5. **入库：** 点击确认，数据被存入 `life_events` 表。

### 第二阶段：频率分析引擎

* **指令：** “分析一下我理发的频率”。
* **逻辑 (技能化后):** * **技能调度器**选择 `query_data_skill`。
* `query_data_skill` **执行器**将问题转化为 SQL：`SELECT event_date FROM life_events WHERE category='haircut' ORDER BY event_date DESC LIMIT 5`。
* 计算平均差值，得出结果：“您平均每 22 天理一次发，建议下周二预约”。



### 第三阶段：主动提醒与报告引擎 (Cron Jobs)

*   **每日简报 (Daily Briefing):** 每天早上（如 08:00），系统自动执行：
    1.  查询 `scheduled_events` 表中所有“今天”的活动。
    2.  结合 `required_items` 字段生成准备清单。
    3.  查询 `life_events` 表分析库存，生成低库存提醒。
    4.  组合成一条消息推送给用户，例如：“早上好！提醒：今天下午4点有游泳课，请准备[游泳包, 泳镜]。另外，冰箱里的牛肉只剩 1kg 了。”

*   **每周总结与计划 (Weekly Summary & Plan):** 每周日晚上（如 20:00），系统自动执行：
    1.  汇总本周 `life_events` 中的开销、活动记录。
    2.  查询 `scheduled_events` 表中“下周”的全部安排。
    3.  生成一份图文并茂的周报，包含本周回顾与下周展望，帮助您规划家庭生活。

---

## 5. 技能目录结构 (建议)

为了更好地组织代码，您可以在 `bot_app` 目录下创建一个 `skills` 目录：

```
bot_app/
├── skills/
│   ├── __init__.py
│   ├── base_skill.py         # (可选) 定义所有技能的基类
│   ├── record_event_skill.py   # 记录生活事件的技能
│   ├── schedule_event_skill.py # 安排未来日程的技能
│   └── query_data_skill.py     # 数据查询与分析的技能
├── main.py                     # 主程序，包含技能调度逻辑
└── ...
```

---

## 6. `docker-compose.yml` 模板预览

为了实现完全免费和本地化的目标，我们将引入 Ollama 服务，并让核心逻辑层与之通信。

```yaml
version: '3.8'

services:
  # 1. 核心逻辑层 (Python + Telegram SDK)
  core_service:
    build: ./bot_app
    environment:
      - TG_TOKEN=${TG_TOKEN}
      - OLLAMA_URL=http://ollama:11434      # [变更] 指向本地 Ollama 服务
      - DB_URL=http://sqlite_service:5000   # 通过内部网络访问数据库
      - CHROMA_URL=http://chroma:8000       # 通过内部网络访问向量库
    depends_on:
      - ollama
      - sqlite_service
      - chroma
    restart: always

  # 2. [新增] 本地 AI 大脑 (Ollama)
  ollama:
    image: ollama/ollama
    volumes:
      - ./ollama_data:/root/.ollama # 将下载的模型持久化到宿主机
    # ports: # 通常不需要将 Ollama 暴露到公网
    #   - "11434:11434"
    restart: unless-stopped
    # 备注: Oracle 的 ARM CPU 性能足够运行 7B-13B 参数的模型。
    # 首次启动后, 您需要进入容器下载模型:
    # docker exec -it [ollama_container_name] ollama pull qwen:7b-chat

  # 3. 结构化数据库 (SQLite via Web API)
  sqlite_service:
    build: ./sqlite_app # 假设您会创建一个简单的 Flask/FastAPI 应用来提供 API
    volumes:
      - ./data:/app/data # 将 SQLite 文件持久化到宿主机
    restart: unless-stopped

  # 4. 向量数据库 (Chroma)
  chroma:
    image: chromadb/chroma:latest
    volumes:
      - ./chroma_data:/chroma/chroma
    restart: unless-stopped

  # 5. 保活/监控 (可选，防止 Oracle 闲置回收)
  keepalive:
    image: alpine
    command: /bin/sh -c "while true; do echo 'alive'; sleep 3600; done"

```

---

## 7. 方案优势总结

1. **完全掌控：** 数据存在你自己的服务器上，不是 Markdown 文件，而是标准数据库。
2. **中英混合无忧：** 通过“识别 -> 确认”闭环，彻底解决语音识别偏差问题。
3. **不废话：** 背景信息（阿德莱德、儿女、工作）存在 `Personal_Info` 表中，仅在回答“全家建议”时按需读取。
4. **主动智能提醒**: 方案内置了定时任务引擎，能主动根据您记录的日程和库存生成每日简报和每周规划，从被动记录变为您的主动生活助理。