#!/usr/bin/env python3
"""
MessageProcessor — 核心业务逻辑层，不依赖任何 Telegram / aiogram 对象。

消息处理完整流程:
  process(text) → ProcessResult（含提取数据，需外部确认）
  confirm(skill_name, extracted_data, raw_text) → bool（写入 DB）

调度提醒内容生成（也可被测试直接调用）:
  generate_daily_reminder() → str
  generate_weekly_preview() → str
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from bot_app.ollama_client import OllamaClient
from bot_app.db_client import DatabaseClient

logger = logging.getLogger(__name__)


# ── 结果数据类 ───────────────────────────────────────────────────────────

@dataclass
class ClarificationRequest:
    """需要向用户追问的上下文。"""
    question: str          # 要展示给用户的问题
    item: str              # 涉及的物品/事项
    intent: str = "remind_to_buy"


@dataclass
class PendingEvent:
    """单条待确认事件。"""
    skill_name: str                                      # "record_event" | "schedule_event"
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""


@dataclass
class ProcessResult:
    """process() 的返回值"""
    success: bool
    # 消息类型: "profile_updated" | "skill_pending" | "events_pending" | "profile_hint" | "error"
    result_type: str
    # 单事件路径（skill_pending）——向后兼容
    skill_name: Optional[str] = None
    extracted_data: Dict[str, Any] = field(default_factory=dict)
    # 多事件路径（events_pending）
    pending_events: List[PendingEvent] = field(default_factory=list)
    # 追问路径（needs_clarification）
    clarification: Optional[ClarificationRequest] = None
    # 背景信息（静默保存后附在结果里供 UI 展示）
    profile_updates: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    # 供 UI 层展示的人类可读摘要
    summary: str = ""


# ── MessageProcessor ─────────────────────────────────────────────────────

class MessageProcessor:
    """
    核心业务逻辑层。

    可在生产代码（aiogram handler）和测试代码中共用，
    完全不依赖 Telegram / aiogram 对象。
    """

    def __init__(self, ollama_client: OllamaClient, db_client: DatabaseClient):
        self.ollama = ollama_client
        self.db = db_client

    # ─── 主入口 ──────────────────────────────────────────────────────────

    async def process(self, text: str) -> ProcessResult:
        """
        处理用户输入文本，返回结构化结果。

        单次 LLM 调用提取所有结构化信息：
          - 背景信息：直接保存到 DB（无需用户确认）
          - 事件（0‥N 条）：返回 skill_pending（单条）或 events_pending（多条）
        """
        if not text or not text.strip():
            return ProcessResult(success=False, result_type="error", error="输入为空")

        # ── 单次统一 LLM 提取 ────────────────────────────────────────────
        try:
            extracted = await self.ollama.extract_all(text)
        except Exception as e:
            logger.error(f"extract_all failed: {e}")
            return ProcessResult(
                success=False, result_type="error", error="无法识别意图，请换种说法"
            )

        # ── 背景信息：规范化后静默保存 ───────────────────────────────────
        raw_profile = extracted.get("profile_updates") or {}
        profile_updates = _normalize_profile_updates(raw_profile)
        if profile_updates:
            ok = await self.db.update_user_profile(profile_updates)
            if not ok:
                logger.warning("update_user_profile returned False; discarding profile_updates")
                profile_updates = {}

        # ── 追问路径：需要先向用户确认补充信息 ──────────────────────────
        raw_clarification = extracted.get("clarification_needed")
        if isinstance(raw_clarification, dict) and raw_clarification.get("question"):
            clarification = ClarificationRequest(
                question=raw_clarification["question"],
                item=raw_clarification.get("item", ""),
                intent=raw_clarification.get("intent", "remind_to_buy"),
            )
            return ProcessResult(
                success=True,
                result_type="needs_clarification",
                clarification=clarification,
                profile_updates=profile_updates,
                summary=clarification.question,
            )

        # ── 收集待确认事件 ───────────────────────────────────────────────
        pending_events: List[PendingEvent] = []

        for event_data in (extracted.get("schedule_events") or []):
            if isinstance(event_data, dict) and event_data.get("title"):
                pending_events.append(
                    PendingEvent(
                        skill_name="schedule_event",
                        extracted_data=event_data,
                        summary=_build_event_summary("schedule_event", event_data),
                    )
                )

        for event_data in (extracted.get("life_events") or []):
            if isinstance(event_data, dict) and event_data.get("item"):
                pending_events.append(
                    PendingEvent(
                        skill_name="record_event",
                        extracted_data=event_data,
                        summary=_build_event_summary("record_event", event_data),
                    )
                )

        # ── 决定返回类型 ─────────────────────────────────────────────────
        if not profile_updates and not pending_events:
            return ProcessResult(
                success=False,
                result_type="profile_hint",
                summary=(
                    "未能从您的输入中提取到有用信息。\n"
                    "可以尝试：\n"
                    "  • 告诉我您的背景：\"我叫张三，住在南澳大利亚\"\n"
                    "  • 记录一个事件：\"今天剪头了\"\n"
                    "  • 安排一个日程：\"每天早上10:15开例会\""
                ),
            )

        if not pending_events:
            # 纯背景信息更新
            summary_lines = ["背景信息已更新："] + [
                f"  {k}: {v}" for k, v in profile_updates.items()
            ]
            return ProcessResult(
                success=True,
                result_type="profile_updated",
                profile_updates=profile_updates,
                summary="\n".join(summary_lines),
            )

        # 构建 profile 部分摘要（如有）
        profile_summary = ""
        if profile_updates:
            keys_str = "、".join(profile_updates.keys())
            profile_summary = f"✅ 背景信息已记录（{keys_str}）"

        if len(pending_events) == 1:
            # 单事件 —— 向后兼容路径
            event = pending_events[0]
            summary_parts = [p for p in [profile_summary, event.summary] if p]
            return ProcessResult(
                success=True,
                result_type="skill_pending",
                skill_name=event.skill_name,
                extracted_data=event.extracted_data,
                profile_updates=profile_updates,
                summary="\n\n".join(summary_parts),
            )

        # 多事件
        summary_parts = [p for p in [profile_summary, f"识别到 {len(pending_events)} 个事项待确认"] if p]
        return ProcessResult(
            success=True,
            result_type="events_pending",
            pending_events=pending_events,
            profile_updates=profile_updates,
            summary="\n\n".join(summary_parts),
        )

    # ─── 确认写库 ────────────────────────────────────────────────────────

    async def confirm(
        self,
        skill_name: str,
        extracted_data: Dict[str, Any],
        raw_text: str = "",
    ) -> bool:
        """
        用户确认后，将提取数据写入数据库。

        Returns:
            bool: 是否写入成功
        """
        if skill_name == "record_event":
            extracted_data["raw_text"] = raw_text
            return await self.db.create_life_event(**extracted_data)
        elif skill_name == "schedule_event":
            return await self.db.create_scheduled_event(**extracted_data)
        else:
            logger.error(f"confirm() called with unknown skill: {skill_name}")
            return False

    # ─── 处理追问回复 ────────────────────────────────────────────────────

    async def process_clarification(
        self,
        item: str,
        original_text: str,
        user_reply: str,
    ) -> ProcessResult:
        """
        用户对追问的回复（如"两三天"）→ 创建提醒 schedule_event 等待确认。

        Returns:
            ProcessResult(result_type="skill_pending", skill_name="schedule_event")
        """
        event_data = await self.ollama.create_reminder_from_reply(item, original_text, user_reply)
        if not event_data:
            return ProcessResult(
                success=False,
                result_type="error",
                error="无法根据您的回答创建提醒，请再描述一下时间（例如：两三天、下周）",
            )

        return ProcessResult(
            success=True,
            result_type="skill_pending",
            skill_name="schedule_event",
            extracted_data=event_data,
            summary=f"✅ 已为「{item}」创建提醒",
        )

    # ─── 提醒内容生成 ────────────────────────────────────────────────────

    async def generate_daily_reminder(self) -> str:
        """生成今日日程提醒文本。无事件时返回空字符串。"""
        events = await self.db.get_todays_events()
        if not events:
            return ""

        lines = ["今天的日程提醒：\n"]
        for e in events:
            title = e.get("title") or e.get("item", "未命名事项")
            person = e.get("person")
            items = e.get("required_items", [])
            item_str = _format_required_items(items)
            who = f"（{person}）" if person else ""
            lines.append(f"• {title}{who}{item_str}")
        return "\n".join(lines)

    async def generate_weekly_preview(self) -> str:
        """生成下周日程预告文本。"""
        events = await self.db.get_scheduled_events(upcoming_only=True, days_ahead=7)
        if not events:
            return "下周没有特别安排，好好休息！"

        lines = ["下周日程预览：\n"]
        for e in events:
            title = e.get("title", "未命名")
            start = (e.get("start_time") or "")[:10] or "时间待定"
            person = e.get("person")
            items = e.get("required_items", [])
            item_str = _format_required_items(items)
            who = f" ({person})" if person else ""
            lines.append(f"• {start} — {title}{who}")
            if item_str:
                lines.append(f"  需要：{item_str.lstrip('，需要带：')}")
        return "\n".join(lines)


# ── 模块级工具函数（可被单元测试直接测试）──────────────────────────────


def _build_event_summary(skill_name: str, data: Dict[str, Any]) -> str:
    """从提取数据构建单行人类可读摘要。"""
    if skill_name == "schedule_event":
        title = data.get("title") or "日程"
        rule = data.get("recurrence_rule") or "一次性"
        return f"✅ 已识别日程：{title}（{rule}）"
    elif skill_name == "record_event":
        item = data.get("item") or "事件"
        qty = data.get("quantity")
        unit = data.get("unit") or ""
        qty_str = f" {qty}{unit}" if qty is not None else ""
        return f"✅ 已识别事件：{item}{qty_str}"
    return f"✅ 已识别：{skill_name}"


def _normalize_profile_updates(updates: Dict[str, Any]) -> Dict[str, Any]:
    """规范化背景信息字段。"""
    normalized: Dict[str, Any] = {}
    for key, value in (updates or {}).items():
        mapped_key = _normalize_profile_key(key)
        if not mapped_key:
            continue
        if value is None:
            continue
        if isinstance(value, str):
            value = value.strip()
            if not value:
                continue
        normalized[mapped_key] = value
    return normalized


def _normalize_profile_key(key: Any) -> Optional[str]:
    """将原始键名归一化为安全的 snake_case。"""
    if not isinstance(key, str):
        return None
    candidate = key.strip().lower()
    if not candidate:
        return None
    candidate = re.sub(r"[^a-z0-9_]+", "_", candidate)
    candidate = re.sub(r"_+", "_", candidate).strip("_")
    if not re.match(r"^[a-z][a-z0-9_]*$", candidate):
        return None
    return candidate


def _format_required_items(items: Any) -> str:
    if isinstance(items, list) and items:
        return f"，需要带：{', '.join(str(i) for i in items)}"
    if isinstance(items, str) and items:
        return f"，需要带：{items}"
    return ""
