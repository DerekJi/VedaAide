"""
共享 fixtures — 供单元测试和集成测试共用。
"""
import asyncio
import os
import tempfile
import pytest
import pytest_asyncio


@pytest.fixture(scope="session")
def event_loop():
    """使用 session 级别的 event loop，避免 aiosqlite 连接复用问题。"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def tmp_db(tmp_path):
    """每个测试使用独立的临时 SQLite 文件，测试结束后自动清理。"""
    from bot_app.db_client import DatabaseClient
    db_path = str(tmp_path / "test.db")
    client = DatabaseClient(db_path=db_path)
    await client.init_db()
    yield client
