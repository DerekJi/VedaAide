#!/usr/bin/env python3
"""
数据库客户端
直接通过 aiosqlite 访问 SQLite 文件，无需中间 HTTP 层。
"""

import aiosqlite
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


_INIT_SQL = [
    """
    CREATE TABLE IF NOT EXISTS life_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        category TEXT NOT NULL,
        person TEXT,
        location TEXT,
        item TEXT,
        quantity REAL,
        unit TEXT,
        notes TEXT,
        raw_text TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS scheduled_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        person TEXT,
        location TEXT,
        category TEXT,
        start_time TIMESTAMP,
        end_time TIMESTAMP,
        recurrence_rule TEXT,
        required_items TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS user_profiles (
        key TEXT PRIMARY KEY,
        value TEXT,
        is_sensitive BOOLEAN DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS background_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_name TEXT NOT NULL UNIQUE,
        description TEXT,
        rule_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
]

# 增量迁移：老数据库缺少的列
_MIGRATIONS = [
    ("life_events",      "person",   "ALTER TABLE life_events ADD COLUMN person TEXT"),
    ("life_events",      "location", "ALTER TABLE life_events ADD COLUMN location TEXT"),
    ("scheduled_events", "person",   "ALTER TABLE scheduled_events ADD COLUMN person TEXT"),
    ("scheduled_events", "location", "ALTER TABLE scheduled_events ADD COLUMN location TEXT"),
    ("scheduled_events", "end_time", "ALTER TABLE scheduled_events ADD COLUMN end_time TIMESTAMP"),
]


class DatabaseClient:
    """
    数据库客户端 — 直接使用 aiosqlite 操作本地 SQLite 文件。
    不依赖任何 HTTP 服务。
    """

    def __init__(self, db_path: str = "./data/vedaaide.db"):
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.db_path = db_path
        logger.info(f"DatabaseClient initialized: {db_path}")

    @asynccontextmanager
    async def _connect(self):
        """异步上下文管理器，自动提交并关闭连接。"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            yield conn

    async def init_db(self):
        """建表 + 增量迁移（启动时调用一次）。"""
        async with self._connect() as conn:
            for sql in _INIT_SQL:
                await conn.execute(sql)
            await conn.commit()

            # 增量迁移
            for table, col, alter_sql in _MIGRATIONS:
                async with conn.execute(f"PRAGMA table_info({table})") as cur:
                    columns = {row[1] async for row in cur}
                if col not in columns:
                    await conn.execute(alter_sql)
                    logger.info(f"Migration: {table}.{col} added")
            await conn.commit()
        logger.info("Database initialized successfully")

    # ─── 生活事件 ────────────────────────────────────────────────────

    async def create_life_event(self, **kwargs) -> bool:
        try:
            async with self._connect() as conn:
                await conn.execute(
                    """
                    INSERT INTO life_events
                        (category, person, location, item, quantity, unit, notes, raw_text)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        kwargs.get("category"),
                        kwargs.get("person"),
                        kwargs.get("location"),
                        kwargs.get("item"),
                        kwargs.get("quantity"),
                        kwargs.get("unit"),
                        kwargs.get("notes"),
                        kwargs.get("raw_text"),
                    ),
                )
                await conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error creating life event: {e}")
            return False

    async def get_life_events(
        self, limit: int = 50, offset: int = 0, category: Optional[str] = None
    ) -> List[Dict]:
        try:
            async with self._connect() as conn:
                if category:
                    sql = "SELECT * FROM life_events WHERE category=? ORDER BY event_date DESC LIMIT ? OFFSET ?"
                    params = (category, limit, offset)
                else:
                    sql = "SELECT * FROM life_events ORDER BY event_date DESC LIMIT ? OFFSET ?"
                    params = (limit, offset)
                async with conn.execute(sql, params) as cur:
                    rows = await cur.fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"Error fetching life events: {e}")
            return []

    # ─── 计划事件 ────────────────────────────────────────────────────

    async def create_scheduled_event(self, **kwargs) -> bool:
        try:
            required_items = kwargs.get("required_items", [])
            if isinstance(required_items, list):
                required_items = json.dumps(required_items, ensure_ascii=False)
            async with self._connect() as conn:
                await conn.execute(
                    """
                    INSERT INTO scheduled_events
                        (title, person, location, category, start_time, end_time,
                         recurrence_rule, required_items, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        kwargs.get("title"),
                        kwargs.get("person"),
                        kwargs.get("location"),
                        kwargs.get("category"),
                        kwargs.get("start_time"),
                        kwargs.get("end_time"),
                        kwargs.get("recurrence_rule"),
                        required_items,
                        kwargs.get("notes"),
                    ),
                )
                await conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error creating scheduled event: {e}")
            return False

    async def get_scheduled_events(
        self,
        upcoming_only: bool = False,
        days_ahead: int = 7,
    ) -> List[Dict]:
        """
        获取计划事件列表。

        Args:
            upcoming_only: 只返回今天起 days_ahead 天内的事件
            days_ahead: 向前看多少天
        """
        try:
            async with self._connect() as conn:
                if upcoming_only:
                    sql = """
                        SELECT * FROM scheduled_events
                        WHERE start_time >= date('now')
                          AND start_time <= date('now', ?)
                        ORDER BY start_time ASC
                    """
                    params = (f"+{days_ahead} days",)
                else:
                    sql = "SELECT * FROM scheduled_events ORDER BY start_time ASC"
                    params = ()
                async with conn.execute(sql, params) as cur:
                    rows = await cur.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                if d.get("required_items"):
                    try:
                        d["required_items"] = json.loads(d["required_items"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                result.append(d)
            return result
        except Exception as e:
            logger.error(f"Error fetching scheduled events: {e}")
            return []

    async def get_todays_events(self) -> List[Dict]:
        """获取今日相关的计划事件（含周期性事件）。"""
        try:
            today_weekday = datetime.now().strftime("%A").upper()[:3]  # MON, TUE, ...
            weekday_rule = f"WEEKLY_{today_weekday}"
            async with self._connect() as conn:
                sql = """
                    SELECT * FROM scheduled_events
                    WHERE recurrence_rule = ?
                       OR date(start_time) = date('now')
                    ORDER BY start_time ASC
                """
                async with conn.execute(sql, (weekday_rule,)) as cur:
                    rows = await cur.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                if d.get("required_items"):
                    try:
                        d["required_items"] = json.loads(d["required_items"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                result.append(d)
            return result
        except Exception as e:
            logger.error(f"Error fetching today's events: {e}")
            return []

    # ─── 用户背景信息 ─────────────────────────────────────────────────

    async def update_user_profile(self, profile_data: Dict[str, Any]) -> bool:
        try:
            async with self._connect() as conn:
                for key, value in profile_data.items():
                    await conn.execute(
                        "INSERT OR REPLACE INTO user_profiles (key, value) VALUES (?, ?)",
                        (key, str(value)),
                    )
                await conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
            return False

    async def get_user_profile(self) -> Dict[str, str]:
        try:
            async with self._connect() as conn:
                async with conn.execute(
                    "SELECT key, value FROM user_profiles WHERE is_sensitive = 0"
                ) as cur:
                    rows = await cur.fetchall()
            return {r["key"]: r["value"] for r in rows}
        except Exception as e:
            logger.error(f"Error fetching user profile: {e}")
            return {}

    # ─── 健康检查 ─────────────────────────────────────────────────────

    async def health_check(self) -> bool:
        try:
            async with self._connect() as conn:
                await conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
