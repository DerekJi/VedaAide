# 📌 历史参考：极简方案对比 (已合并)

**状态：已合并至 Architecture.md**

本文档保留作为历史参考，记录 DeepSeek 提出的"极简化"方案思路。该方案的核心优势（Skill 层解耦、MVP 优先）已被采纳并整合至最终的 [Architecture.md](Architecture.md) 中。

---

## 核心贡献点

DeepSeek 极简方案在以下方面为最终技术方案提供了宝贵的设计参考：

### 1. Skill 层高度解耦

- 每个 Skill 只负责一类功能
- 便于独立开发、测试和优化
- 易于后续扩展新功能而无需修改现有逻辑

### 2. MVP 优先策略

- 第一阶段只实现最小集合（`record_event_skill` + `schedule_event_skill`）
- 快速验证核心"识别→确认→入库"流程
- 避免初期过度设计，降低项目复杂度

### 3. 成本与维护对比

- 清晰对比了本地部署（Ollama）vs 云端 API（GPT-4o-mini）的成本差异
- 为长期运维提供了预算预期和决策依据

---

## 最终采纳的方案

见 **[Architecture.md](Architecture.md)**，该文档融合了两个方案的最优设计

**Gemini 方案贡献：**
- ✅ 完整的微服务体系架构
- ✅ 数据隐私和自主控制理念
- ✅ 四层组件的完整设计（Bot / Brain / DB / Memory）

**DeepSeek 方案贡献：**
- ✅ Skill 层的高度解耦和模块化
- ✅ MVP 优先的分阶段实施策略
- ✅ 成本与可维护性的平衡分析

**最终融合方案特点：**
- 🎯 Docker Compose 容器化 + Ollama 本地大模型
- 🎯 MVP 第一阶段：2 周完成核心"识别→确认→入库"
- 🎯 阶段二：3-4 周添加定时提醒和报告能力
- 🎯 阶段三：5 周后完整功能和前端
- 🎯 成本：Oracle 免费实例 + Ollama 免费 = 长期零成本

---

## 参考资源

- **完整设计**：[Architecture.md](Architecture.md)
- **项目概览**：[README.md](../README.md)
- **数据迁移**：[Migration_Guide.md](Migration_Guide.md)

---

## 附：DeepSeek 原方案要点（存档）

以下为 DeepSeek 提出的快速记录日常事件
* **半结构化事件解析**：邮件或截图中的活动信息（如 camping 活动）
* **智能提醒**：

  * 当日活动提醒（Daily Briefing）
  * 周度总结与下周计划
* **零干扰记忆**：

  * 只存储你允许的个人信息
  * LLM 只用于解析意图和结构化信息，不做闲聊

---

## 2. 技术架构（极简版）

```
用户输入（文本 / OCR输出）
        │
        ▼
Azure Function (入口)
        │
        ▼
GPT‑4o‑mini (Intent & Entity Extraction)
        │
        ▼
Skill Router → 对应 Skill
        │
        ▼
Azure Table Storage
        ├─ scheduled_events
        ├─ life_events
        └─ checklists
        │
        ▼
Daily Briefing / Weekly Summary
        │
        ▼
Telegram / QQ / Webbot 通知
```

### 组件说明

1. **输入层**：

   * 支持文本消息
   * OCR 处理可以沿用豆包 App
   * Telegram 或 QQ Bot（可选）作为消息入口

2. **意图解析层**：

   * 调用 **Azure OpenAI GPT‑4o‑mini** 解析文本 → JSON
   * JSON 示例：

     ```json
     {
       "intent": "garbage_bin_query",
       "date": "2026-03-11",
       "details": {}
     }
     ```

3. **Skill 层**：

   * 每个 Skill 只负责一类功能，逻辑确定：

     | Skill                | 功能          |
     | -------------------- | ----------- |
     | record_event_skill   | 记录一次性事件     |
     | schedule_event_skill | 安排周期性或未来事件  |
     | garbage_bin_skill    | 根据规则生成垃圾桶推送 |
     | inventory_skill      | 物品库存分析      |
     | checklist_skill      | 从活动生成准备清单   |
     | statistics_skill     | 分析频率、周期性活动  |

4. **存储层**：

   * Azure Table Storage
   * `scheduled_events` 存未来或周期性活动
   * `life_events` 存一次性事件
   * `checklists` 存准备清单

5. **提醒层**：

   * Azure Function 定时触发：

     * **每日简报**：汇总当天活动、提醒、checklist
     * **周报**：汇总一周记录、下周安排

---

## 3. 极简化理由

* **不需要容器化**：Functions + Table Storage 已经可以完全满足
* **AI 调用量最小**：LLM 仅用于意图解析和 JSON 抽取
* **成本低**：GPT‑4o‑mini 调用频率低，token 消耗小
* **易维护**：没有本地 VM 或 Ollama server

---

## 4. 后续扩展思路

### A. AI 层扩展

* 将 GPT‑4o‑mini 替换成更高级模型（GPT‑4o / LLaMA / Ollama 本地部署）
* 支持复杂问答或建议生成（如：孩子活动安排优化）

### B. 输入渠道扩展

* 支持直接接收邮件内容（IMAP / Gmail / Outlook API）
* 支持拍照/扫描文档（本地 OCR 或 Azure Computer Vision OCR）

### C. Memory 层扩展

* 增加向量数据库（如 ChromaDB）存“软记忆”，支持模糊查询和偏好推理
* 为每个 Skill 增加独立配置和历史上下文，便于 AI 个性化建议

### D. Skill 扩展

* 增加更多自动化功能：

  * 天气提醒 / 运动安排 / 饮食记录
  * 孩子作业、课外活动管理
  * 库存管理自动补充提醒

### E. 前端扩展

* Web App / 手机 App 展示日程和清单
* 多渠道推送（Telegram / QQ / 微信 / SMS）
* 可视化周报、提醒、统计图表

---

## 5. 开发优先级建议

1. **第一阶段（1-2周）**

   * Azure Function + Table Storage
   * GPT‑4o‑mini 意图解析
   * record_event / schedule_event / garbage_bin_skill
   * 每日简报功能

2. **第二阶段**

   * checklist_skill、inventory_skill
   * 支持邮件/截图输入
   * 周报生成

3. **第三阶段（可选）**

   * 向量数据库软记忆
   * 模型升级（Ollama / 高级 GPT）
   * 多渠道前端

---

✅ **核心理念**：

> “AI 只做理解和抽取，规则和提醒都由 Skill 层完成。”

这样极简又可扩展，成本低，后续升级也很容易。

