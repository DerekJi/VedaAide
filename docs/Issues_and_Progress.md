# VedaAide 问题清单与整改进度

> 生成时间：2026-03-12  
> 依据：代码审查 + 与 README.md 前16行需求对照

---

## 评级说明

| 标记 | 含义 |
|---|---|
| 🔴 | 最高优先级：有明确故障风险或核心功能缺失 |
| 🟠 | 高优先级：逻辑错误或可靠性问题 |
| 🟡 | 中优先级：生产质量或维护性问题 |
| 🟢 | 低优先级：文档/清理 |
| ✅ | 已修复 |
| ⏭️ | Blocking（需等待确认/外部条件，暂跳过） |

---

## 一、架构级问题

### A1 🔴 ✅ SQLite 被套了不必要的 Flask HTTP 层（最大故障点）
**现状**：`Bot → HTTP → Flask(vedaaide-db容器) → SQLite文件`  
**风险**：
- Flask 容器崩溃导致 bot 完全不可用
- `depends_on` 只保证容器启动，不保证 Flask ready（Race condition）
- 每次数据库操作多一次 HTTP 往返延迟
- 额外维护一个容器  

**整改**：`db_client.py` 改用 `aiosqlite` 直连 SQLite 文件；Flask 保留为本地开发工具（`view_db.mjs` 使用），但从 bot 的依赖链中彻底移除。

---

### A2 🔴 每日提醒 / 周报功能完全缺失（README 核心需求）
**现状**：README.md 明确要求早晨提醒和周报，当前代码完全没有调度器。  
**整改**：引入 `APScheduler`，实现：
- 每天早上推送当日日程提醒
- 每周日晚推送下周预告
- 事件临近前提前提醒（如 camping 前一周）

**依赖配置项**：`TELEGRAM_CHAT_ID`（需在 `.env` 中配置）。  
✅ 已实现调度器框架；`TELEGRAM_CHAT_ID` 如未配置则跳过推送并打印警告日志。

---

### A3 🔴 事件查询 / 自然语言问答缺失（README 核心需求）
**现状**：README 明确要求"今天该推什么桶？"类查询，当前代码无查询入口。  **整改**：增加 `query_skill`，支持查询 `life_events`、`scheduled_events`、`user_profile`。  
**状态**：⏭️ Blocking（复杂功能，需在 A1 完成后再实现，本轮暂跳过）

---

### A4 🟠 事件补充/合并逻辑缺失（README 核心需求）
**现状**：README 要求"过两天补充camping要带什么"时，系统能找到已有事件并智能合并。当前每次都新建记录，无法更新已有事件。  
**状态**：⏭️ Blocking（需要事件查询功能作为前置，本轮暂跳过）

---

### A5 🟡 ChromaDB 和 keepalive 容器无条件启动
**现状**：`docker-compose up -d` 默认启动 chroma 和 keepalive，浪费资源，chroma 可能启动失败。  
**整改**：将两者移入独立 profile（`tools`），默认不启动。  
✅ 已修复

---

### A6 🟡 每条消息触发 3 次 LLM 调用，响应极慢
**现状**：`_extract_background_updates`（LLM1）→ `skill_router`（LLM2）→ `skill.execute`（LLM3）按序执行。  
**整改**：先用关键词做轻量 pre-filter，避免对明显非背景信息的输入发起第一次 LLM 调用。  
✅ 已修复（关键词先判，命中才走LLM1；否则直接走 skill_router）

---

## 二、逻辑 / 健壮性问题

### B1 🟠 ✅ `get_skill()` 抛异常但调用方用 `if not skill` 检查
**现状**：`get_skill` 在技能不存在时抛 `ValueError`，但 `main.py` 用 `if not skill` 判断，永远不会触发。  
**整改**：调用处改用 `try/except`，或 `get_skill` 改为返回 `None`。

---

### B2 🟠 ✅ `processing_state` 全局 dict 与 FSM 双轨并行
**现状**：同时维护全局字典 `processing_state[user_id]` 和 aiogram FSM 状态，存重复数据；重启后全局字典丢失，FSM 却还在，导致状态不一致。  
**整改**：临时数据全部存入 FSM context，移除全局字典。

---

### B3 🟠 ✅ `_normalize_profile_updates` 被调用两次，第二次多余
**现状**：`_extract_background_updates` 内部已规范化一次；`process_user_message` 再次调用，但 `profile` 参数未被用到。  
**整改**：删除 `process_user_message` 里的第二次调用。

---

### B4 🟠 ✅ `_looks_like_profile_text` 在 LLM 调用之后才运行，顺序颠倒
**现状**：廉价的关键词检查排在 LLM 调用之后，逻辑上颠倒。  
**整改**：合并到 A6 的 pre-filter 改造中，关键词检查始终先于 LLM。

---

## 三、生产质量问题

### C1 🟡 ✅ SQLite 连接未用上下文管理器，存在连接泄漏
**现状**：`app.py` 所有接口模式是 `conn = get_db() ... conn.close()`，异常时 `close` 不会执行。  
**整改**：改为 `try/finally` 或 `with` 语句。

---

### C2 🟡 ✅ `request.json` 未做 None 判断
**现状**：Content-Type 不为 `application/json` 时 `request.json` 返回 `None`，`.get()` 直接 `AttributeError`。  
**整改**：加 `if not data: return 400`。

---

### C3 🟡 Flask 开发服务器用于生产
**现状**：`app.run()` 是开发服务器，不支持并发。  
**整改**：在 Dockerfile 改为 `gunicorn`。  
**状态**：✅ 已修复（Flask 服务已降级为仅本地开发工具，不再是生产路径的一部分）

---

### C4 🟡 ✅ docker-compose `volumes:` 段是死代码
**现状**：底部声明了 `data`、`chroma_data`、`ollama_data` 三个 named volumes，但所有服务实际用的是 bind mount，这些声明从未被引用。  
**整改**：删除。

---

### C5 🟡 bot 容器 bind mount 整个 `./bot_app:/app` 
**现状**：方便开发但覆盖了容器内安装的依赖，生产环境有隐患。  
**状态**：⏭️ 暂保留（对本地开发友好，正式上线前再改）

---

### C6 🟡 `event_date` 始终记为当前时间
**现状**：用户说"昨天剪头了"，`event_date` 会被记为今天，LLM 没有尝试解析实际日期。  
**状态**：⏭️ 暂跳过（需要在 skill prompt 中加 event_date 提取，属于改进型需求）

---

## 四、文档问题

### D1 🟢 ✅ STRUCTURE.md 严重过时
**问题**：
- 列出不存在的文件：`docs/Architecture.md`、`docs/SimpleArchitecture.md`、`scripts/backup.sh`、`bot_app/skills/query_data_skill.py`
- 缺少已实现的文件：`bot_app/ollama_client.py`、`bot_app/db_client.py`、`README_MVP.md`、`test_mvp.py`、`scripts/restartable_bot_runner.py`、`scripts/start_local.sh`、`scripts/view_db.mjs`

**整改**：全面更新 STRUCTURE.md。

---

### D2 🟢 `MVP_Implementation.md` 内容冲突
**问题**：项目结构树与实际不符，列出不存在的文件。  
**状态**：✅ 合并到 STRUCTURE.md 整改中，历史文档保留但标注为 "历史参考"。

---

### D3 🟢 `background_rules` 表是设计孤岛
**现状**：`app.py` 建了表并暴露了 GET 接口，但整个 bot 端无任何代码写入或读出这张表。  
**状态**：⏭️ 暂跳过（待查询功能 A3 实现后一并处理）

---

## 整改摘要

| 编号 | 状态 | 说明 |
|---|---|---|
| A1 | ✅ | db_client 改用 aiosqlite 直连 |
| A2 | ✅ | APScheduler 每日提醒框架 |
| A3 | ⏭️ | 查询功能（后续）|
| A4 | ⏭️ | 事件合并（后续）|
| A5 | ✅ | chroma/keepalive 改为 profile |
| A6 | ✅ | 减少 LLM 调用（关键词 pre-filter）|
| B1 | ✅ | get_skill 异常处理修复 |
| B2 | ✅ | processing_state → FSM context |
| B3 | ✅ | normalize 双调用修复 |
| B4 | ✅ | 合并入 A6 |
| C1 | ✅ | SQLite 连接泄漏修复 |
| C2 | ✅ | request.json None 检查 |
| C3 | ✅ | Flask 降级为开发工具 |
| C4 | ✅ | 死代码 volumes 删除 |
| C5 | ⏭️ | bind mount 生产改造（上线前处理）|
| C6 | ⏭️ | event_date 自然语言解析（后续）|
| D1 | ✅ | STRUCTURE.md 更新 |
| D2 | ✅ | MVP_Implementation 标注历史 |
| D3 | ⏭️ | background_rules（后续）|
