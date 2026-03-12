"""
集成测试 — MessageProcessor 完整流程（不使用真实 Ollama / Telegram）
覆盖：IT-01 IT-02 IT-03 IT-05 IT-06 IT-07 + 复合路由 + 多事件路径 + 追问流程
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from bot_app.message_processor import MessageProcessor


# ── Helpers ───────────────────────────────────────────────────────────────

def make_ollama(
    *,
    profile_updates: dict | None = None,
    schedule_events: list | None = None,
    life_events: list | None = None,
    clarification_needed: dict | None = None,
    raise_exc: Exception | None = None,
):
    """构造 OllamaClient 的最小 Mock（新架构：extract_all 单次调用）。"""
    mock = MagicMock()
    if raise_exc is not None:
        mock.extract_all = AsyncMock(side_effect=raise_exc)
    else:
        mock.extract_all = AsyncMock(return_value={
            "profile_updates": profile_updates or {},
            "schedule_events": schedule_events or [],
            "life_events": life_events or [],
            "clarification_needed": clarification_needed or None,
        })
    return mock


# ── IT-01: 记录事件完整流程 ───────────────────────────────────────────────

class TestRecordEventFlow:
    @pytest.mark.asyncio
    async def test_process_returns_skill_pending(self, tmp_db):
        ollama = make_ollama(
            life_events=[{"category": "haircut", "item": "理发", "quantity": 1, "unit": "次", "notes": ""}],
        )
        processor = MessageProcessor(ollama, tmp_db)
        result = await processor.process("今天剪头了")

        assert result.success is True
        assert result.result_type == "skill_pending"
        assert result.skill_name == "record_event"
        assert result.extracted_data.get("category") == "haircut"

    @pytest.mark.asyncio
    async def test_confirm_saves_to_db(self, tmp_db):
        ollama = make_ollama(
            life_events=[{"category": "haircut", "item": "理发", "quantity": 1, "unit": "次", "notes": ""}],
        )
        processor = MessageProcessor(ollama, tmp_db)
        result = await processor.process("今天剪头了")

        ok = await processor.confirm(
            result.skill_name, result.extracted_data, "今天剪头了"
        )
        assert ok is True

        events = await tmp_db.get_life_events(limit=10)
        assert len(events) == 1
        assert events[0]["category"] == "haircut"

    @pytest.mark.asyncio
    async def test_confirm_persists_raw_text(self, tmp_db):
        ollama = make_ollama(
            life_events=[{"category": "grocery", "item": "牛肉", "quantity": 2, "unit": "kg", "notes": ""}],
        )
        processor = MessageProcessor(ollama, tmp_db)
        result = await processor.process("在超市买了2kg牛肉")
        await processor.confirm(result.skill_name, result.extracted_data, "在超市买了2kg牛肉")

        events = await tmp_db.get_life_events(limit=10)
        assert events[0].get("raw_text") == "在超市买了2kg牛肉"


# ── IT-02: 计划事件完整流程 ───────────────────────────────────────────────

class TestScheduleEventFlow:
    @pytest.mark.asyncio
    async def test_process_returns_skill_pending(self, tmp_db):
        ollama = make_ollama(
            schedule_events=[{
                "title": "游泳课", "category": "swimming", "start_time": None,
                "recurrence_rule": "WEEKLY_TUE", "required_items": ["泳镜"], "notes": "",
            }],
        )
        processor = MessageProcessor(ollama, tmp_db)
        result = await processor.process("孩子每周二有游泳课")

        assert result.success is True
        assert result.result_type == "skill_pending"
        assert result.skill_name == "schedule_event"
        assert result.extracted_data.get("recurrence_rule") == "WEEKLY_TUE"

    @pytest.mark.asyncio
    async def test_confirm_saves_to_db(self, tmp_db):
        ollama = make_ollama(
            schedule_events=[{
                "title": "游泳课", "category": "swimming", "start_time": None,
                "recurrence_rule": "WEEKLY_TUE", "required_items": ["泳镜"], "notes": "",
            }],
        )
        processor = MessageProcessor(ollama, tmp_db)
        result = await processor.process("孩子每周二有游泳课")
        ok = await processor.confirm(result.skill_name, result.extracted_data, "孩子每周二有游泳课")

        assert ok is True
        events = await tmp_db.get_scheduled_events(upcoming_only=False)
        assert len(events) == 1
        assert events[0]["title"] == "游泳课"


# ── IT-03: 背景信息覆盖更新 ───────────────────────────────────────────────

class TestProfileUpdateFlow:
    @pytest.mark.asyncio
    async def test_profile_text_updates_db(self, tmp_db):
        ollama = make_ollama(
            profile_updates={"self_name": "张三", "self_birthday": "1978-01-16"},
        )
        processor = MessageProcessor(ollama, tmp_db)
        result = await processor.process("我叫张三，1978年1月16号出生")

        assert result.success is True
        assert result.result_type == "profile_updated"
        assert "self_name" in result.profile_updates

        profile = await tmp_db.get_user_profile()
        assert profile.get("self_name") == "张三"

    @pytest.mark.asyncio
    async def test_profile_overwrite_same_key(self, tmp_db):
        ollama = make_ollama(profile_updates={"self_name": "李四"})
        processor = MessageProcessor(ollama, tmp_db)
        await processor.process("我叫李四")

        # 再更新一次
        ollama2 = make_ollama(profile_updates={"self_name": "王五"})
        processor2 = MessageProcessor(ollama2, tmp_db)
        await processor2.process("我叫王五")

        profile = await tmp_db.get_user_profile()
        assert profile.get("self_name") == "王五"

    @pytest.mark.asyncio
    async def test_profile_hint_when_llm_returns_empty(self, tmp_db):
        """LLM 返回空提取结果时，返回 profile_hint。"""
        ollama = make_ollama()  # all empty
        processor = MessageProcessor(ollama, tmp_db)
        result = await processor.process("我现在是Youi的Senior Developer")

        assert result.result_type in ("profile_hint", "error")


# ── IT-05: 每日提醒生成 ───────────────────────────────────────────────────

class TestDailyReminderGeneration:
    @pytest.mark.asyncio
    async def test_generates_with_todays_event(self, tmp_db):
        today_abbr = datetime.now().strftime("%a").upper()  # e.g. "MON"
        await tmp_db.create_scheduled_event(
            title="游泳课",
            category="swimming",
            recurrence_rule=f"WEEKLY_{today_abbr}",
            required_items=["泳镜"],
        )

        processor = MessageProcessor(MagicMock(), tmp_db)
        text = await processor.generate_daily_reminder()

        assert "游泳课" in text

    @pytest.mark.asyncio
    async def test_returns_empty_string_when_no_events(self, tmp_db):
        processor = MessageProcessor(MagicMock(), tmp_db)
        text = await processor.generate_daily_reminder()
        assert text == ""


# ── IT-06: 周报生成 ───────────────────────────────────────────────────────

class TestWeeklyPreviewGeneration:
    @pytest.mark.asyncio
    async def test_generates_with_upcoming_event(self, tmp_db):
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT10:00:00")
        await tmp_db.create_scheduled_event(
            title="医生预约",
            category="doctor",
            start_time=tomorrow,
            required_items=["身份证"],
        )

        processor = MessageProcessor(MagicMock(), tmp_db)
        text = await processor.generate_weekly_preview()

        assert "医生预约" in text

    @pytest.mark.asyncio
    async def test_returns_placeholder_when_no_events(self, tmp_db):
        processor = MessageProcessor(MagicMock(), tmp_db)
        text = await processor.generate_weekly_preview()
        assert "没有" in text or text == "下周没有特别安排，好好休息！"


# ── IT-07: 错误链路 ───────────────────────────────────────────────────────

class TestErrorPaths:
    @pytest.mark.asyncio
    async def test_empty_input_returns_error(self, tmp_db):
        processor = MessageProcessor(MagicMock(), tmp_db)
        result = await processor.process("")

        assert result.success is False
        assert result.result_type == "error"

    @pytest.mark.asyncio
    async def test_whitespace_only_returns_error(self, tmp_db):
        processor = MessageProcessor(MagicMock(), tmp_db)
        result = await processor.process("   ")

        assert result.success is False
        assert result.result_type == "error"

    @pytest.mark.asyncio
    async def test_extract_all_raises_returns_error(self, tmp_db):
        """extract_all 抛出异常时，返回 error。"""
        ollama = make_ollama(raise_exc=Exception("LLM timeout"))
        processor = MessageProcessor(ollama, tmp_db)
        result = await processor.process("今天剪头了")

        assert result.success is False
        assert result.result_type == "error"

    @pytest.mark.asyncio
    async def test_empty_extraction_returns_profile_hint(self, tmp_db):
        """extract_all 返回全空时，返回 profile_hint。"""
        ollama = make_ollama()  # all empty
        processor = MessageProcessor(ollama, tmp_db)
        result = await processor.process("balabala 无法识别")

        assert result.result_type == "profile_hint"
        assert result.success is False

    @pytest.mark.asyncio
    async def test_confirm_with_unknown_skill_returns_false(self, tmp_db):
        processor = MessageProcessor(MagicMock(), tmp_db)
        ok = await processor.confirm("unknown_skill", {}, "raw")
        assert ok is False


# ── 复合路由：背景信息 + 事件同时出现 ─────────────────────────────────────

class TestCompoundRouting:
    @pytest.mark.asyncio
    async def test_profile_saved_silently_and_schedule_pending(self, tmp_db):
        """复合消息：背景信息静默保存，日程返回 skill_pending 等待确认。"""
        ollama = make_ollama(
            profile_updates={"job_title": "Senior Developer", "employer": "Youi", "work_mode": "remote"},
            schedule_events=[{
                "title": "每日例会", "category": "meeting",
                "start_time": "2026-03-12T10:15:00", "end_time": None,
                "recurrence_rule": "DAILY", "required_items": [],
                "notes": "AEDT夏时制，约4月后需调整",
            }],
        )
        processor = MessageProcessor(ollama, tmp_db)
        result = await processor.process(
            "我现在是Youi的Senior Developer，每天都是远程工作。现在是南澳的夏时制，早上10:15开例会"
        )

        # 日程等待确认（单事件走 skill_pending 路径）
        assert result.success is True
        assert result.result_type == "skill_pending"
        assert result.skill_name == "schedule_event"
        assert result.extracted_data.get("recurrence_rule") == "DAILY"

        # 背景信息已静默保存
        assert result.profile_updates
        profile = await tmp_db.get_user_profile()
        assert profile  # DB 中确实存了

    @pytest.mark.asyncio
    async def test_compound_summary_mentions_profile(self, tmp_db):
        """复合结果的 summary 应同时提示背景信息已记录。"""
        ollama = make_ollama(
            profile_updates={"employer": "Youi"},
            schedule_events=[{
                "title": "例会", "category": "meeting",
                "start_time": None, "recurrence_rule": "DAILY", "required_items": [],
            }],
        )
        processor = MessageProcessor(ollama, tmp_db)
        result = await processor.process("我在Youi工作，每天有例会")

        assert "背景信息" in result.summary

    @pytest.mark.asyncio
    async def test_multiple_events_returns_events_pending(self, tmp_db):
        """多个事件时返回 events_pending，而非 skill_pending。"""
        ollama = make_ollama(
            schedule_events=[
                {"title": "游泳课", "category": "swimming", "start_time": None,
                 "recurrence_rule": "WEEKLY_TUE", "required_items": [], "notes": ""},
            ],
            life_events=[
                {"category": "haircut", "item": "理发", "quantity": 1, "unit": "次", "notes": ""},
            ],
        )
        processor = MessageProcessor(ollama, tmp_db)
        result = await processor.process("今天剪头了，另外孩子每周二有游泳课")

        assert result.success is True
        assert result.result_type == "events_pending"
        assert len(result.pending_events) == 2

    @pytest.mark.asyncio
    async def test_compound_profile_only_saves_silently_no_event(self, tmp_db):
        """背景信息解析失败（事件也无），只有背景信息时正确保存并返回 profile_updated。"""
        ollama = make_ollama(profile_updates={"employer": "Youi"})
        processor = MessageProcessor(ollama, tmp_db)
        result = await processor.process("我在Youi工作")

        assert result.result_type == "profile_updated"
        assert result.profile_updates
        profile = await tmp_db.get_user_profile()
        assert profile.get("employer") == "Youi"


# ── 追问流程 ──────────────────────────────────────────────────────────────

class TestClarificationFlow:
    @pytest.mark.asyncio
    async def test_low_stock_triggers_clarification(self, tmp_db):
        """「牙膏快没了」应触发追问，而非直接记录为 life_event。"""
        ollama = make_ollama(
            clarification_needed={
                "question": "你觉得现在还能用几天？",
                "item": "牙膏",
                "intent": "remind_to_buy",
            }
        )
        processor = MessageProcessor(ollama, tmp_db)
        result = await processor.process("牙膏快没了，可能要换新的了")

        assert result.success is True
        assert result.result_type == "needs_clarification"
        assert result.clarification is not None
        assert result.clarification.item == "牙膏"
        assert "几天" in result.clarification.question

    @pytest.mark.asyncio
    async def test_clarification_reply_creates_reminder(self, tmp_db):
        """用户回答「两三天」→ 创建 schedule_event 类型提醒。"""
        reminder_event = {
            "title": "检查并购买牙膏",
            "category": "shopping",
            "start_time": "2026-03-14T09:00:00",
            "end_time": None,
            "recurrence_rule": None,
            "required_items": [],
            "notes": "原消息：牙膏快没了，可能要换新的了",
        }

        ollama = MagicMock()
        ollama.create_reminder_from_reply = AsyncMock(return_value=reminder_event)

        processor = MessageProcessor(ollama, tmp_db)
        result = await processor.process_clarification(
            item="牙膏",
            original_text="牙膏快没了，可能要换新的了",
            user_reply="两三天",
        )

        assert result.success is True
        assert result.result_type == "skill_pending"
        assert result.skill_name == "schedule_event"
        assert result.extracted_data.get("title") == "检查并购买牙膏"

    @pytest.mark.asyncio
    async def test_clarification_reply_confirmed_saves_to_db(self, tmp_db):
        """追问→回答→确认 完整流程，最终写入数据库。"""
        reminder_event = {
            "title": "检查并购买牙膏",
            "category": "shopping",
            "start_time": "2026-03-14T09:00:00",
            "end_time": None,
            "recurrence_rule": None,
            "required_items": [],
            "notes": "牙膏快没了",
        }

        ollama = MagicMock()
        ollama.create_reminder_from_reply = AsyncMock(return_value=reminder_event)

        processor = MessageProcessor(ollama, tmp_db)
        result = await processor.process_clarification("牙膏", "牙膏快没了", "大概两天")

        ok = await processor.confirm(result.skill_name, result.extracted_data, "")
        assert ok is True

        events = await tmp_db.get_scheduled_events(upcoming_only=False)
        assert any(e["title"] == "检查并购买牙膏" for e in events)

    @pytest.mark.asyncio
    async def test_clarification_llm_failure_returns_error(self, tmp_db):
        """create_reminder_from_reply 返回 None 时，返回 error。"""
        ollama = MagicMock()
        ollama.create_reminder_from_reply = AsyncMock(return_value=None)

        processor = MessageProcessor(ollama, tmp_db)
        result = await processor.process_clarification("牙膏", "牙膏快没了", "两三天")

        assert result.success is False
        assert result.result_type == "error"

