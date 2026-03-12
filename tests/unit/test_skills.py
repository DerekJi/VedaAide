"""
单元测试 — RecordEventSkill.parse_result 和 ScheduleEventSkill.parse_result
不调用 Ollama / DB；全部是纯 parse_result 逻辑测试。
"""
import json
import pytest
from bot_app.skills.record_event_skill import RecordEventSkill
from bot_app.skills.schedule_event_skill import ScheduleEventSkill


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def record_skill():
    return RecordEventSkill(ollama_client=None, db_client=None)


@pytest.fixture
def schedule_skill():
    return ScheduleEventSkill(ollama_client=None, db_client=None)


# ── RecordEventSkill.parse_result ─────────────────────────────────────────

class TestRecordEventSkillParseResult:
    def test_clean_json(self, record_skill):
        text = '{"category":"haircut","item":"理发","quantity":1,"unit":"次","notes":""}'
        result = record_skill.parse_result(text)
        assert result is not None
        assert result["category"] == "haircut"
        assert result["item"] == "理发"

    def test_fenced_json(self, record_skill):
        text = '```json\n{"category":"grocery","item":"牛肉","quantity":2,"unit":"kg","notes":""}\n```'
        result = record_skill.parse_result(text)
        assert result is not None
        assert result["category"] == "grocery"

    def test_json_with_preamble(self, record_skill):
        text = '好的，提取结果如下：\n{"category":"cooking_use","item":"鸡蛋","quantity":5,"unit":"个","notes":""}'
        result = record_skill.parse_result(text)
        assert result is not None
        assert result["item"] == "鸡蛋"

    def test_quantity_string_to_float(self, record_skill):
        text = '{"category":"grocery","item":"苹果","quantity":"3","unit":"个"}'
        result = record_skill.parse_result(text)
        assert result is not None
        assert isinstance(result["quantity"], float)
        assert result["quantity"] == 3.0

    def test_missing_required_category_returns_none(self, record_skill):
        text = '{"item":"牛肉","quantity":2,"unit":"kg"}'
        result = record_skill.parse_result(text)
        assert result is None

    def test_missing_required_item_returns_none(self, record_skill):
        text = '{"category":"grocery","quantity":2,"unit":"kg"}'
        result = record_skill.parse_result(text)
        assert result is None

    def test_plain_text_returns_none(self, record_skill):
        result = record_skill.parse_result("无法理解")
        assert result is None

    def test_trailing_comma_fixed(self, record_skill):
        text = '{"category":"haircut","item":"理发","quantity":1,}'
        result = record_skill.parse_result(text)
        assert result is not None
        assert result["category"] == "haircut"

    def test_get_prompt_not_empty(self, record_skill):
        prompt = record_skill.get_prompt()
        assert len(prompt) > 50
        assert "JSON" in prompt


# ── ScheduleEventSkill.parse_result ──────────────────────────────────────

class TestScheduleEventSkillParseResult:
    def _weekly_json(self, rule: str) -> str:
        return json.dumps({
            "title": "游泳课",
            "person": "Marco",
            "category": "swimming",
            "start_time": None,
            "end_time": None,
            "recurrence_rule": rule,
            "required_items": ["泳镜", "游泳包"],
            "notes": "",
        }, ensure_ascii=False)

    def test_weekly_event(self, schedule_skill):
        result = schedule_skill.parse_result(self._weekly_json("WEEKLY_TUE"))
        assert result is not None
        assert result["title"] == "游泳课"
        assert result["recurrence_rule"] == "WEEKLY_TUE"

    def test_required_items_list(self, schedule_skill):
        result = schedule_skill.parse_result(self._weekly_json("WEEKLY_TUE"))
        assert isinstance(result["required_items"], list)
        assert "泳镜" in result["required_items"]

    def test_one_time_event(self, schedule_skill):
        text = json.dumps({
            "title": "医生预约",
            "category": "doctor",
            "start_time": "2026-04-15T15:00:00",
            "end_time": None,
            "recurrence_rule": None,
            "required_items": ["身份证"],
            "notes": "",
        }, ensure_ascii=False)
        result = schedule_skill.parse_result(text)
        assert result is not None
        assert result["category"] == "doctor"
        assert result["start_time"] == "2026-04-15T15:00:00"

    def test_invalid_start_time_cleared(self, schedule_skill):
        text = json.dumps({
            "title": "医生预约",
            "category": "doctor",
            "start_time": "not-a-date",
            "recurrence_rule": None,
            "required_items": [],
        }, ensure_ascii=False)
        result = schedule_skill.parse_result(text)
        assert result is not None
        assert result["start_time"] is None

    def test_missing_title_returns_none(self, schedule_skill):
        text = '{"category":"doctor","start_time":null}'
        result = schedule_skill.parse_result(text)
        assert result is None

    def test_missing_category_returns_none(self, schedule_skill):
        text = '{"title":"游泳课","start_time":null}'
        result = schedule_skill.parse_result(text)
        assert result is None

    def test_required_items_as_string_normalised(self, schedule_skill):
        text = json.dumps({
            "title": "露营",
            "category": "camping",
            "start_time": None,
            "recurrence_rule": None,
            "required_items": "睡袋,帐篷,头灯",
        }, ensure_ascii=False)
        result = schedule_skill.parse_result(text)
        assert result is not None
        assert isinstance(result["required_items"], list)
        assert len(result["required_items"]) == 3

    def test_fenced_json(self, schedule_skill):
        inner = json.dumps({
            "title": "篮球训练",
            "category": "basketball",
            "start_time": None,
            "recurrence_rule": "WEEKLY_MON",
            "required_items": [],
        }, ensure_ascii=False)
        text = f"```json\n{inner}\n```"
        result = schedule_skill.parse_result(text)
        assert result is not None
        assert result["title"] == "篮球训练"

    def test_get_prompt_not_empty(self, schedule_skill):
        prompt = schedule_skill.get_prompt()
        assert len(prompt) > 50
        assert "JSON" in prompt
