#!/usr/bin/env python3
"""
计划事件技能 (ScheduleEventSkill)
用于记录未来或周期性事件，如：孩子的课程、医生预约等
"""

from typing import Dict, Any, Optional, List, Tuple
import json
import re
import logging
from datetime import datetime, timedelta
from .base_skill import BaseSkill

logger = logging.getLogger(__name__)


class ScheduleEventSkill(BaseSkill):
    """
    计划周期性/未来事件的技能
    
    示例输入：
    - "孩子每周二有游泳课"
    - "下周二下午3点要去看医生"
    - "camping 在3月20日，需要准备睡袋、帐篷、头灯"
    
    提取字段：
    - title: 事件名称
    - person: 相关人员（如 Marco / self）
    - location: 地点
    - category: 事件类别
    - start_time: 开始时间
    - end_time: 结束时间
    - recurrence_rule: 递推规则 （如 WEEKLY_TUE）
    - required_items: 需要准备的物品列表
    - notes: 备注
    """
    
    def get_name(self) -> str:
        return "schedule_event"
    
    def get_description(self) -> str:
        return "计划周期性或未来事件"
    
    def get_prompt(self) -> str:
        """
        高度优化的 Prompt，专注于提取事件计划信息
        """
        return """你是一个活动计划助手。
你的任务是从用户的自然语言描述中提取结构化的事件计划信息。

请从用户输入中提取以下信息，并返回严格的 JSON 格式（无其他文本）：
{
    "title": "事件标题",
    "person": "相关人员，例如: Marco, self, null",
    "location": "地点，例如: Parafield Recreation Center, null",
    "category": "事件类别，例如: swimming(游泳), basketball(篮球), doctor(医生), camping(露营), music(音乐), scout(童子军), other",
    "start_time": "开始时间 ISO8601 格式，例如: 2026-03-15T15:00:00 或 null 如果不确定",
    "end_time": "结束时间 ISO8601 格式，例如: 2026-03-15T16:30:00 或 null 如果不确定",
    "recurrence_rule": "递推规则，例如: DAILY(每天/每日), WEEKLY_MON(每周一), WEEKLY_TUE(每周二), BIWEEKLY(每两周), MONTHLY(每月), null 如果是一次性事件",
    "required_items": ["所需物品1", "所需物品2"],
    "notes": "其他备注"
}

重要规则：
1. start_time 使用 ISO8601 格式：YYYY-MM-DDTHH:MM:SS
2. 如果输入包含时间段（如 6.30-8.00），请同时给出 start_time 与 end_time
3. 对于"每周X"的表述，使用 WEEKLY_MON(周一)、WEEKLY_TUE(周二) 等格式
4. 对于"每天/每日"的表述，使用 DAILY
5. 时间词换算：早上/上午=AM原值，下午/晚上=+12h（如 早上10:15 → T10:15:00，下午3点 → T15:00:00）
6. 如果时间依赖夏令时/时区（如"夏时制"），在 notes 中标注，例如：notes: "AEDT夏时制，约4月后需调整"
7. required_items 是一个字符串数组
8. 如果没有具体时间，start_time 可以是 null
9. 严格返回 JSON，不要有任何其他说明文字

示例：
- 用户: "孩子每周二有游泳课"
    返回: {"title":"游泳课","person":"孩子","category":"swimming","start_time":null,"end_time":null,"recurrence_rule":"WEEKLY_TUE","required_items":["游泳包","泳镜"],"notes":""}
  
- 用户: "下周一下午3点要去看医生，需要带身份证和保险卡"
    返回: {"title":"医生预约","category":"doctor","start_time":"2026-03-17T15:00:00","end_time":null,"recurrence_rule":null,"required_items":["身份证","保险卡"],"notes":""}
  
- 用户: "camping 在3月20日，需要准备睡袋、帐篷、头灯"
    返回: {"title":"Camping","category":"camping","start_time":"2026-03-20T00:00:00","end_time":null,"recurrence_rule":null,"required_items":["睡袋","帐篷","头灯"],"notes":""}"""

    async def execute(self, user_input: str) -> Dict[str, Any]:
        """执行并用规则对 LLM 结果做补全，提升稳定性。"""
        result = await super().execute(user_input)

        if result.get("success") and result.get("data"):
            enriched = self._enrich_with_user_input(result["data"], user_input)
            result["data"] = enriched
            result["message"] = (
                f"✅ 已识别为：{self.get_description()}\n\n提取的信息：\n{self._format_data(enriched)}"
            )
            return result

        # 当 LLM 解析失败时，尝试从原始文本提取最小可用结构
        fallback = self._extract_from_user_input(user_input)
        if fallback:
            return {
                "success": True,
                "data": fallback,
                "message": f"✅ 已识别为：{self.get_description()}\n\n提取的信息：\n{self._format_data(fallback)}"
            }

        return result
    
    def parse_result(self, text: str) -> Optional[Dict[str, Any]]:
        """
        从 Ollama 输出中解析 JSON
        
        Args:
            text: Ollama 返回的文本
            
        Returns:
            Optional[Dict]: 解析的 JSON，或 None
        """
        try:
            text = text.strip()

            candidates = [text]
            # 兼容 ```json ...``` / ``` ...``` 返回
            fenced = re.findall(r'```(?:json)?\s*(.*?)\s*```', text, flags=re.DOTALL | re.IGNORECASE)
            candidates.extend(fenced)

            # 兼容前置说明文字，只截取从第一个 "{" 开始的内容
            brace_start = text.find('{')
            if brace_start != -1:
                candidates.append(text[brace_start:])

            for candidate in candidates:
                parsed = self._try_parse_json(candidate)
                if parsed is not None:
                    return self._validate_schema(parsed)

            # 最后兜底：即使 JSON 截断，也尽量抽取核心字段
            fallback = self._extract_minimal_fields(text)
            if fallback is not None:
                return self._validate_schema(fallback)

            logger.warning(f"Failed to parse JSON from: {text[:160]}")
            return None
            
        except Exception as e:
            logger.error(f"Error parsing result: {str(e)}")
            return None

    def _try_parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        """尝试将文本解析为 JSON，包含常见输出噪声修复。"""
        if not text:
            return None

        candidate = text.strip()
        if not candidate:
            return None

        # 第一次直接解析
        try:
            data = json.loads(candidate)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            pass

        # 清理常见问题：智能引号、结尾逗号、截断未闭合
        candidate = candidate.replace('“', '"').replace('”', '"').replace("‘", "'").replace("’", "'")
        candidate = re.sub(r',\s*([}\]])', r'\1', candidate)

        if '{' in candidate and '}' not in candidate:
            # 处理模型输出被截断但核心字段已输出的情况
            candidate = candidate.rstrip()
            candidate = re.sub(r',\s*$', '', candidate)
            candidate = candidate + '}'

        # 只保留第一个 JSON 对象范围
        start = candidate.find('{')
        end = candidate.rfind('}')
        if start != -1 and end != -1 and end > start:
            candidate = candidate[start:end + 1]

        try:
            data = json.loads(candidate)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None

    def _extract_minimal_fields(self, text: str) -> Optional[Dict[str, Any]]:
        """从半结构化文本里兜底提取 title/category。"""
        title_match = re.search(r'"title"\s*:\s*"([^"]+)"', text)
        category_match = re.search(r'"category"\s*:\s*"([^"]+)"', text)

        if not title_match or not category_match:
            return None

        return {
            "title": title_match.group(1).strip(),
            "person": None,
            "location": None,
            "category": category_match.group(1).strip(),
            "start_time": None,
            "end_time": None,
            "recurrence_rule": None,
            "required_items": [],
            "notes": ""
        }

    def _extract_from_user_input(self, user_input: str) -> Optional[Dict[str, Any]]:
        """不依赖 LLM，从用户输入中抽取最小结构。"""
        text = user_input.strip()
        if not text:
            return None

        title = "计划事件"
        category = "other"

        if "篮球" in text:
            title = "篮球训练" if "训练" in text else "篮球活动"
            category = "basketball"
        elif "游泳" in text:
            title = "游泳课"
            category = "swimming"
        elif "医生" in text or "医院" in text:
            title = "医生预约"
            category = "doctor"

        data = {
            "title": title,
            "person": None,
            "location": None,
            "category": category,
            "start_time": None,
            "end_time": None,
            "recurrence_rule": None,
            "required_items": [],
            "notes": "",
        }
        return self._enrich_with_user_input(data, text)

    def _enrich_with_user_input(self, data: Dict[str, Any], user_input: str) -> Dict[str, Any]:
        """使用规则补全周几、时间、标题等字段。"""
        text = user_input.strip()

        # 标题纠偏：避免出现“训练计划确认”这类无效标题
        if "篮球" in text:
            current_title = str(data.get("title") or "")
            if (not current_title) or ("确认" in current_title) or ("事件" in current_title):
                data["title"] = "篮球训练"

        if "篮球" in text and (not data.get("category") or data.get("category") == "other"):
            data["category"] = "basketball"

        if not data.get("person"):
            data["person"] = self._extract_person(text)

        if not data.get("location"):
            data["location"] = self._extract_location(text)

        weekday_rule, weekday_idx = self._extract_weekly_rule(text)
        if weekday_rule and not data.get("recurrence_rule"):
            data["recurrence_rule"] = weekday_rule

        start_hm, end_hm = self._extract_time_range(text)
        if start_hm and not data.get("start_time"):
            start_dt = self._next_occurrence(weekday_idx, start_hm)
            data["start_time"] = start_dt.isoformat(timespec="seconds")
            if end_hm and not data.get("end_time"):
                end_dt = start_dt.replace(hour=end_hm[0], minute=end_hm[1], second=0, microsecond=0)
                if end_dt <= start_dt:
                    end_dt = end_dt + timedelta(days=1)
                data["end_time"] = end_dt.isoformat(timespec="seconds")

        # 把地点/对象信息放入备注，避免信息丢失
        notes = str(data.get("notes") or "").strip()
        person = self._extract_person(text)
        if person and person not in notes:
            notes = f"{notes}; 对象: {person}".strip("; ") if notes else f"对象: {person}"
        if end_hm and "结束时间" not in notes:
            notes = f"{notes}; 结束时间: {end_hm[0]:02d}:{end_hm[1]:02d}".strip("; ") if notes else f"结束时间: {end_hm[0]:02d}:{end_hm[1]:02d}"
        data["notes"] = notes

        return data

    def _extract_weekly_rule(self, text: str) -> Tuple[Optional[str], Optional[int]]:
        mapping = {
            "一": ("WEEKLY_MON", 0),
            "二": ("WEEKLY_TUE", 1),
            "三": ("WEEKLY_WED", 2),
            "四": ("WEEKLY_THU", 3),
            "五": ("WEEKLY_FRI", 4),
            "六": ("WEEKLY_SAT", 5),
            "日": ("WEEKLY_SUN", 6),
            "天": ("WEEKLY_SUN", 6),
        }
        m = re.search(r"每周([一二三四五六日天])", text)
        if not m:
            return None, None
        return mapping[m.group(1)]

    def _extract_time_range(self, text: str) -> Tuple[Optional[Tuple[int, int]], Optional[Tuple[int, int]]]:
        # 例：下午6.00-7.30 / 18:00-19:30 / 下午6:00到7:30
        m = re.search(
            r"(上午|下午|晚上|中午)?\s*(\d{1,2})(?:[:.：](\d{1,2}))?\s*[-~到]\s*(\d{1,2})(?:[:.：](\d{1,2}))?",
            text,
        )
        if not m:
            return None, None

        period = m.group(1) or ""
        sh = int(m.group(2))
        sm = int(m.group(3) or 0)
        eh = int(m.group(4))
        em = int(m.group(5) or 0)

        sh = self._apply_period(sh, period)
        eh = self._apply_period(eh, period)
        return (sh, sm), (eh, em)

    def _apply_period(self, hour: int, period: str) -> int:
        if period in ("下午", "晚上") and hour < 12:
            return hour + 12
        if period == "中午" and hour < 11:
            return hour + 12
        return hour

    def _next_occurrence(self, weekday_idx: Optional[int], hm: Tuple[int, int]) -> datetime:
        now = datetime.now()
        target = now

        if weekday_idx is not None:
            days = (weekday_idx - now.weekday()) % 7
            target = now + timedelta(days=days)

        target = target.replace(hour=hm[0], minute=hm[1], second=0, microsecond=0)

        # 当天同一时刻已过，则顺延到下一周
        if weekday_idx is not None and target <= now:
            target = target + timedelta(days=7)

        return target

    def _extract_location(self, text: str) -> Optional[str]:
        m = re.search(
            r"在\s*([^，。,]+?)(?:篮球训练|游泳课|训练|要|$)",
            text,
            flags=re.IGNORECASE,
        )
        if not m:
            return None
        return m.group(1).strip()

    def _extract_person(self, text: str) -> Optional[str]:
        if "我自己" in text or "我本人" in text:
            return "self"

        m = re.search(r"([A-Za-z][A-Za-z\s]{1,24})要", text)
        if m:
            return m.group(1).strip()

        m = re.search(r"([\u4e00-\u9fff]{1,4})要", text)
        if m:
            return m.group(1).strip()

        if "我" in text:
            return "self"

        return None
    
    def _validate_schema(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        验证提取的数据是否符合 Schema
        
        Args:
            data: 要验证的数据
            
        Returns:
            Optional[Dict]: 验证通过的数据，或 None
        """
        required_fields = ['title', 'category']
        
        # 检查必需字段
        for field in required_fields:
            if field not in data or not data[field]:
                logger.warning(f"Missing required field: {field}")
                return None
        
        # 确保 required_items 是数组
        if 'required_items' not in data:
            data['required_items'] = []
        elif not isinstance(data['required_items'], list):
            if isinstance(data['required_items'], str):
                # 尝试解析字符串为数组
                data['required_items'] = [item.strip() for item in data['required_items'].split(',')]
            else:
                data['required_items'] = []
        
        # 验证 start_time 格式（如果提供）
        if data.get('start_time'):
            try:
                datetime.fromisoformat(data['start_time'])
            except (ValueError, TypeError):
                logger.warning(f"Invalid start_time format: {data['start_time']}")
                data['start_time'] = None

        # 验证 end_time 格式（如果提供）
        if data.get('end_time'):
            try:
                datetime.fromisoformat(data['end_time'])
            except (ValueError, TypeError):
                logger.warning(f"Invalid end_time format: {data['end_time']}")
                data['end_time'] = None
        
        return data
    
    async def save_to_db(self, data: Dict[str, Any]) -> bool:
        """
        将事件数据保存到数据库
        
        Args:
            data: 提取的事件数据
            
        Returns:
            bool: 是否保存成功
        """
        if not self.db_client:
            logger.warning("Database client not initialized")
            return False
        
        try:
            # 调用数据库 API
            response = await self.db_client.post(
                '/api/scheduled_events',
                json={
                    'title': data.get('title'),
                    'person': data.get('person'),
                    'location': data.get('location'),
                    'category': data.get('category'),
                    'start_time': data.get('start_time'),
                    'end_time': data.get('end_time'),
                    'recurrence_rule': data.get('recurrence_rule'),
                    'required_items': data.get('required_items', []),
                    'notes': data.get('notes', '')
                }
            )
            
            if response.status_code == 201:
                logger.info(f"Successfully saved scheduled event to database: {data}")
                return True
            else:
                logger.error(f"Failed to save scheduled event: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error saving scheduled event to database: {str(e)}")
            return False
