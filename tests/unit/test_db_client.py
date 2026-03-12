"""
单元测试 — DatabaseClient
覆盖 IT 层的数据读写基础：不依赖任何外部服务。
"""
import pytest
import pytest_asyncio


# ── 辅助 fixture ──────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db(tmp_db):
    """直接复用 conftest 中的 tmp_db。"""
    return tmp_db


# ── 生活事件 ─────────────────────────────────────────────────────────────

class TestLifeEvents:
    @pytest.mark.asyncio
    async def test_create_and_read(self, db):
        ok = await db.create_life_event(
            category="haircut", item="理发", quantity=1, unit="次",
            raw_text="今天剪头了"
        )
        assert ok is True

        events = await db.get_life_events()
        assert len(events) == 1
        assert events[0]["category"] == "haircut"
        assert events[0]["item"] == "理发"
        assert events[0]["quantity"] == 1

    @pytest.mark.asyncio
    async def test_create_with_person_and_location(self, db):
        await db.create_life_event(
            category="grocery", item="牛肉", quantity=2, unit="kg",
            person="self", location="Woolworths", raw_text="在 Woolworths 买了 2kg 牛肉"
        )
        events = await db.get_life_events()
        assert events[0]["person"] == "self"
        assert events[0]["location"] == "Woolworths"

    @pytest.mark.asyncio
    async def test_filter_by_category(self, db):
        await db.create_life_event(category="haircut", item="理发", quantity=1, unit="次")
        await db.create_life_event(category="grocery", item="猪肉", quantity=1, unit="kg")

        haircuts = await db.get_life_events(category="haircut")
        assert len(haircuts) == 1
        assert haircuts[0]["category"] == "haircut"

    @pytest.mark.asyncio
    async def test_multiple_events_ordered_desc(self, db):
        for i in range(3):
            await db.create_life_event(category="other", item=f"item{i}", quantity=i)
        events = await db.get_life_events()
        assert len(events) == 3

    @pytest.mark.asyncio
    async def test_missing_required_fields_handled(self, db):
        # category 必填，item 可选；不应崩溃
        ok = await db.create_life_event(category="other")
        assert ok is True


# ── 计划事件 ─────────────────────────────────────────────────────────────

class TestScheduledEvents:
    @pytest.mark.asyncio
    async def test_create_weekly_event(self, db):
        ok = await db.create_scheduled_event(
            title="游泳课",
            category="swimming",
            recurrence_rule="WEEKLY_TUE",
            required_items=["游泳包", "泳镜"],
            person="孩子"
        )
        assert ok is True

        events = await db.get_scheduled_events()
        assert len(events) == 1
        e = events[0]
        assert e["title"] == "游泳课"
        assert e["recurrence_rule"] == "WEEKLY_TUE"
        assert isinstance(e["required_items"], list)
        assert "游泳包" in e["required_items"]

    @pytest.mark.asyncio
    async def test_create_one_time_event(self, db):
        await db.create_scheduled_event(
            title="牙医",
            category="doctor",
            start_time="2026-04-10T15:00:00",
            required_items=["身份证", "保险卡"]
        )
        events = await db.get_scheduled_events()
        assert events[0]["start_time"] == "2026-04-10T15:00:00"
        assert events[0]["recurrence_rule"] is None

    @pytest.mark.asyncio
    async def test_get_todays_events_weekly(self, db):
        """写入今天星期几对应的周期事件，应能从 get_todays_events 里查到。"""
        from datetime import datetime
        today_abbr = datetime.now().strftime("%A").upper()[:3]  # MON / TUE ...
        rule = f"WEEKLY_{today_abbr}"
        await db.create_scheduled_event(title="今日测试", recurrence_rule=rule)

        today_events = await db.get_todays_events()
        titles = [e["title"] for e in today_events]
        assert "今日测试" in titles

    @pytest.mark.asyncio
    async def test_get_todays_events_excludes_other_days(self, db):
        """写入非今天的周期事件，不应出现在今日提醒里。"""
        from datetime import datetime
        today_abbr = datetime.now().strftime("%A").upper()[:3]
        # 找一个不是今天的星期
        all_days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        other_day = next(d for d in all_days if d != today_abbr)
        await db.create_scheduled_event(title="非今日", recurrence_rule=f"WEEKLY_{other_day}")

        today_events = await db.get_todays_events()
        titles = [e["title"] for e in today_events]
        assert "非今日" not in titles


# ── 用户背景信息 ──────────────────────────────────────────────────────────

class TestUserProfile:
    @pytest.mark.asyncio
    async def test_write_and_read(self, db):
        ok = await db.update_user_profile({"son_name": "Marco", "current_city": "Sydney"})
        assert ok is True

        profile = await db.get_user_profile()
        assert profile["son_name"] == "Marco"
        assert profile["current_city"] == "Sydney"

    @pytest.mark.asyncio
    async def test_overwrite_same_key(self, db):
        await db.update_user_profile({"son_name": "Marco"})
        await db.update_user_profile({"son_name": "Luca"})

        profile = await db.get_user_profile()
        assert profile["son_name"] == "Luca"
        # 只有一条记录
        keys = list(profile.keys())
        assert keys.count("son_name") == 1

    @pytest.mark.asyncio
    async def test_empty_profile(self, db):
        profile = await db.get_user_profile()
        assert profile == {}


# ── 健康检查 ──────────────────────────────────────────────────────────────

class TestDbHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_ok(self, db):
        ok = await db.health_check()
        assert ok is True
