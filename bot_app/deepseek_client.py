#!/usr/bin/env python3
"""
DeepSeek API 客户端
使用 OpenAI 兼容接口与 DeepSeek 通信，接口与 OllamaClient 完全一致。
"""

import httpx
import json
import logging
import os
import re
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """
    DeepSeek API 客户端

    与 OllamaClient 保持相同的公共接口（extract_all / create_reminder_from_reply / health_check），
    可直接替换使用，无需修改 MessageProcessor 或测试代码。
    """

    BASE_URL = "https://api.deepseek.com"

    def __init__(self, api_key: str = "", model: str = "deepseek-chat"):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.model = os.getenv("DEEPSEEK_MODEL", model)
        self.timeout = 120

        if not self.api_key:
            raise ValueError("❌ DEEPSEEK_API_KEY environment variable not set!")

        logger.info(f"Initialized DeepSeekClient, model: {self.model}")

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        top_p: float = 0.9,
        **kwargs,          # 吸收 OllamaClient 独有的 stream/system 等参数，保持兼容
    ) -> str:
        """向 DeepSeek 发送 chat completions 请求，返回文本响应。"""
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "top_p": top_p,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                if resp.status_code != 200:
                    error_msg = f"DeepSeek error ({resp.status_code}): {resp.text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                data = resp.json()
                return data["choices"][0]["message"]["content"]

            except httpx.TimeoutException:
                error_msg = f"DeepSeek request timeout after {self.timeout} seconds"
                logger.error(error_msg)
                raise Exception(error_msg)
            except Exception as e:
                logger.error(f"Error calling DeepSeek: {e}")
                raise

    def _parse_unified_json(self, text: str) -> Optional[Dict[str, Any]]:
        """从 LLM 返回文本中解析 JSON 对象，处理常见输出格式问题。"""
        if not text:
            return None

        candidate = text.strip()

        try:
            data = json.loads(candidate)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            pass

        fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", candidate, re.IGNORECASE)
        if fenced:
            try:
                data = json.loads(fenced.group(1).strip())
                return data if isinstance(data, dict) else None
            except json.JSONDecodeError:
                pass

        candidate = candidate.replace("\u201c", '"').replace("\u201d", '"')
        candidate = candidate.replace("\u2018", "'").replace("\u2019", "'")
        candidate = re.sub(r",\s*([}\]])", r"\1", candidate)

        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(candidate[start : end + 1])
                return data if isinstance(data, dict) else None
            except json.JSONDecodeError:
                pass

        return None

    async def extract_all(self, text: str) -> Dict[str, Any]:
        """
        单次统一提取：从用户输入中同时提取背景信息、日程事件、生活事件和追问。

        Returns:
            dict，包含：
              profile_updates:      Dict[str, Any]  — 背景信息键值对，无则 {}
              schedule_events:      List[Dict]       — 日程事件列表，无则 []
              life_events:          List[Dict]       — 生活事件列表，无则 []
              clarification_needed: Dict | None      — 需要追问时非 null，含 question/item/intent
        """
        today = datetime.now().strftime("%Y-%m-%d")

        prompt = f"""分析以下用户输入，提取所有信息并以 JSON 格式返回。今天日期：{today}

【返回格式】
{{
  "profile_updates": {{
    "任意snake_case键名": "对应值"
  }},
  "schedule_events": [
    {{
      "title": "事件标题",
      "person": "相关人员或null",
      "location": "地点或null",
      "category": "swimming|basketball|doctor|camping|music|scout|meeting|work|other",
      "start_time": "ISO8601格式如2026-03-15T10:15:00，或null",
      "end_time": "ISO8601格式，或null",
      "recurrence_rule": "DAILY|WEEKLY_MON|WEEKLY_TUE|WEEKLY_WED|WEEKLY_THU|WEEKLY_FRI|WEEKLY_SAT|WEEKLY_SUN|BIWEEKLY|MONTHLY，或null",
      "required_items": ["物品1"],
      "notes": "其他备注"
    }}
  ],
  "life_events": [
    {{
      "category": "haircut|grocery|consumption|entertainment|health|other",
      "person": "相关人员或null",
      "location": "地点或null",
      "item": "具体项目",
      "quantity": null,
      "unit": "单位如kg/次/个，或null",
      "notes": "其他备注"
    }}
  ],
  "clarification_needed": {{
    "question": "追问用户的问题，例如：你觉得现在还能用几天？",
    "item": "涉及的物品或事项，例如：牙膏",
    "intent": "remind_to_buy"
  }}
}}

注意：clarification_needed 仅在用户提到某物品/情况"快没了/快用完了/需要换/需要补充/快到期"但未说明具体何时购买/补充时才填写，其他情况设为 null

【提取规则】
背景信息（profile_updates）：职业、居住地、时区、工作习惯、家庭成员等描述性信息。
  推荐键名：job_title, current_city, timezone, immigration_country, work_mode,
           self_name, son_name, daughter_name, son_birthday, daughter_birthday
  如遇新字段，使用合适的英文 snake_case 名称

日程事件（schedule_events）：将来要做的事或周期性安排
  - 周几规则：每周一→WEEKLY_MON，每周二→WEEKLY_TUE，…，每天/每日→DAILY
  - 时间换算：早上/上午=AM原值，下午/晚上=+12h（下午3点→15:00:00）
  - 含夏令时/时区相关描述时，在 notes 中标注（例如：AEDT夏时制，约4月后需调整）

生活事件（life_events）：已发生的一次性消费或活动
  - 购物→grocery，理发→haircut，吃了/吃掉→consumption，健康相关→health
  - 「快没了/需要换/快用完了」不是已发生的消费，不填入 life_events

clarification_needed（追问）：当用户提到某物品快用完/快没了/需要补充，但未说明具体何时购买
  - 只填写追问问题和物品名，intent 固定为 "remind_to_buy"
  - 此时 life_events 中不要录入该物品（因购买动作尚未发生）
  - 如不需要追问，返回 null

规则：
1. 四类信息互不干扰，一段话可同时包含多类
2. 如某类没有信息，返回空对象 {{}} / 空数组 [] / null
3. 严格返回 JSON，不要有任何说明文字

用户输入：{text}"""

        empty: Dict[str, Any] = {
            "profile_updates": {},
            "schedule_events": [],
            "life_events": [],
            "clarification_needed": None,
        }

        try:
            raw = await self.generate(prompt=prompt, temperature=0.1, top_p=0.3)
            parsed = self._parse_unified_json(raw)

            if not parsed:
                retry_prompt = (
                    f'仅返回 JSON 对象，格式如：{{"profile_updates": {{}}, "schedule_events": [], "life_events": []}}\n\n'
                    f"用户输入：{text}"
                )
                raw2 = await self.generate(retry_prompt, temperature=0.0, top_p=0.1)
                parsed = self._parse_unified_json(raw2)

            if parsed:
                result: Dict[str, Any] = {
                    "profile_updates": parsed.get("profile_updates") or {},
                    "schedule_events": parsed.get("schedule_events") or [],
                    "life_events": parsed.get("life_events") or [],
                    "clarification_needed": parsed.get("clarification_needed") or None,
                }
                logger.info(
                    f"extract_all: profile_keys={list(result['profile_updates'].keys())}, "
                    f"schedule={len(result['schedule_events'])}, "
                    f"life={len(result['life_events'])}, "
                    f"clarification={'yes' if result['clarification_needed'] else 'no'}"
                )
                return result

            logger.warning("extract_all: both parse attempts failed, returning empty")
            return empty

        except Exception as e:
            logger.error(f"Error in extract_all: {e}")
            return empty

    async def create_reminder_from_reply(
        self, item: str, original_text: str, user_reply: str
    ) -> Optional[Dict[str, Any]]:
        """
        根据用户对追问的回答，创建一个购买/补充提醒的 schedule_event。

        Returns:
            schedule_event dict，或 None（解析失败）
        """
        today = datetime.now().strftime("%Y-%m-%d")
        prompt = f"""用户之前说："{original_text}"
用户回答还能用多久："{user_reply}"
今天日期：{today}

请理解用户的口语时间表达，计算提醒日期（在预计用完前 1 天），生成一个购买提醒。

口语时间理解示例（今天 {today}）：
- "两三天" / "再等两三天" / "两三天吧" → 加 2 天
- "一周" / "还有一周" / "大概一周" → 加 6 天
- "周末" / "这个周末" → 最近的周六
- "下周" / "下个星期" → 下周一
- "明天" → 加 1 天
- "半个月" → 加 14 天

仅返回如下 JSON（无其他文字）：
{{
  "title": "检查并购买{item}",
  "person": null,
  "location": null,
  "category": "shopping",
  "start_time": "ISO8601格式日期，如 2026-03-14T09:00:00",
  "end_time": null,
  "recurrence_rule": null,
  "required_items": [],
  "notes": "原消息：{original_text}"
}}"""

        try:
            raw = await self.generate(prompt=prompt, temperature=0.1, top_p=0.3)
            result = self._parse_unified_json(raw)
            if result and result.get("title"):
                return result
            logger.warning(f"create_reminder_from_reply: parse failed, raw={raw[:80]}")
            return None
        except Exception as e:
            logger.error(f"Error in create_reminder_from_reply: {e}")
            return None

    async def health_check(self) -> bool:
        """检查 DeepSeek API 是否可达。"""
        try:
            result = await self.generate("回复：ok", temperature=0.0, top_p=0.1)
            return bool(result)
        except Exception as e:
            logger.error(f"DeepSeek health check failed: {e}")
            return False
