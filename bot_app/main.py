#!/usr/bin/env python3
"""
VedaAide Telegram 机器人
主程序入口 — 薄 Telegram 适配层，核心业务逻辑由 MessageProcessor 处理。
"""

import os
import logging
from typing import Dict, Any

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import asyncio
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot_app.deepseek_client import DeepSeekClient
from bot_app.db_client import DatabaseClient
from bot_app.message_processor import MessageProcessor, PendingEvent, ClarificationRequest

# 本地运行时自动加载 .env；Docker 场景下环境变量会直接注入。
load_dotenv()

# 配置日志（支持 LOG_LEVEL 环境变量）
_log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, _log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 环境配置（变量名与 .env.example 保持一致）
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DB_PATH = os.getenv("DB_PATH", "./data/vedaaide.db")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN environment variable not set!")

# 初始化客户端
bot = Bot(token=TELEGRAM_TOKEN)
ollama_client = DeepSeekClient(api_key=DEEPSEEK_API_KEY)
db_client = DatabaseClient(db_path=DB_PATH)
processor = MessageProcessor(ollama_client=ollama_client, db_client=db_client)
dp = Dispatcher()

# FSM 状态定义
class ProcessingStates(StatesGroup):
    waiting_for_confirmation = State()
    waiting_for_clarification = State()


async def startup_check():
    """启动检查：初始化数据库，验证 Ollama 服务。"""
    logger.info("🚀 Starting VedaAide bot...")
    await db_client.init_db()
    logger.info("✅ Database initialized")

    if await ollama_client.health_check():
        logger.info("✅ Ollama service is running")
    else:
        logger.warning("⚠️ Ollama service is not available")


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """
    /start 命令
    """
    text = (
        "👋 欢迎使用 VedaAide - 生活助手机器人\n\n"
        "📝 您可以：\n"
        "• 告诉我发生的事情（机器人会记住）\n"
        "• 告诉我计划安排（我会提醒您）\n"
        "• 查询背景信息\n\n"
        "💡 示例：\n"
        "• 「今天剪头了」→ 记录一个一次性事件\n"
        "• 「孩子每周二有游泳课」→ 记录一个定期事件\n"
        "• 「我有两个孩子，分别是张三和李四」→ 更新背景信息\n\n"
        "📱 只需要告诉我，剩下的交给我来处理！"
    )
    
    await message.answer(text)


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """
    /help 命令
    """
    text = (
        "🆘 帮助\n\n"
        "VedaAide 支持以下功能：\n\n"
        "1️⃣ 记录事件\n"
        "   说：「今天剪头了」\n"
        "   我会记录：类别=理发，物品=理发\n\n"
        "2️⃣ 记录日程\n"
        "   说：「明天下午3点要去医院」\n"
        "   我会提醒您\n\n"
        "3️⃣ 更新背景信息\n"
        "   说：「我有两个孩子」\n"
        "   我会记住这个信息\n\n"
        "📌 每条消息处理流程：\n"
        "1. 我先识别您的意图\n"
        "2. 提取关键信息\n"
        "3. 显示结果供您确认\n"
        "4. 您确认后保存到数据库\n"
    )
    
    await message.answer(text)


@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    """查看当前已保存的背景信息。"""
    data = await db_client.get_user_profile()
    if not data:
        await message.answer("📭 当前没有已保存的背景信息。")
        return

    lines = ["📘 已保存背景信息："]
    for k, v in data.items():
        lines.append(f"• {k}: {v}")
    await message.answer("\n".join(lines))


@dp.message(StateFilter(None), F.text)
async def process_user_message(message: types.Message, state: FSMContext):
    """处理用户消息 — 委托给 MessageProcessor，handler 只负责 Telegram 交互层。"""
    processing_msg = await message.answer("⏳ 正在处理您的消息...")

    try:
        result = await processor.process(message.text)

        if result.result_type == "profile_updated":
            await processing_msg.edit_text(f"✅ {result.summary}")

        elif result.result_type == "profile_hint":
            await processing_msg.edit_text(f"📝 {result.summary}")

        elif result.result_type == "skill_pending":
            await state.update_data(
                skill_name=result.skill_name,
                extracted_data=result.extracted_data,
                raw_text=message.text,
            )
            formatted = _format_extracted_data(result.extracted_data)
            response_text = (
                f"✅ 识别成功\n\n"
                f"技能: {result.skill_name}\n\n"
                f"提取数据:\n{formatted}\n\n"
                f"请确认是否保存到数据库？"
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✅ 确认入库", callback_data="confirm"),
                InlineKeyboardButton(text="❌ 重新识别", callback_data="reject"),
            ]])
            await processing_msg.edit_text(response_text, reply_markup=keyboard)
            await state.set_state(ProcessingStates.waiting_for_confirmation)

        elif result.result_type == "events_pending":
            events_for_state = [
                {"skill_name": e.skill_name, "data": e.extracted_data}
                for e in result.pending_events
            ]
            await state.update_data(
                pending_events=events_for_state,
                raw_text=message.text,
            )
            lines = [f"✅ 识别成功，共提取到 {len(result.pending_events)} 个事项：\n"]
            for i, event in enumerate(result.pending_events, 1):
                skill_display = "日程安排" if event.skill_name == "schedule_event" else "生活事件"
                formatted = _format_extracted_data(event.extracted_data)
                lines.append(f"【事项 {i}】{skill_display}\n{formatted}")
            lines.append("\n请确认是否全部保存到数据库？")
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✅ 全部确认入库", callback_data="confirm"),
                InlineKeyboardButton(text="❌ 全部取消", callback_data="reject"),
            ]])
            await processing_msg.edit_text("\n\n".join(lines), reply_markup=keyboard)
            await state.set_state(ProcessingStates.waiting_for_confirmation)

        elif result.result_type == "needs_clarification":
            clarification = result.clarification
            await state.update_data(
                clarification_item=clarification.item,
                clarification_intent=clarification.intent,
                clarification_original_text=message.text,
            )
            await processing_msg.edit_text(f"🤔 {clarification.question}")
            await state.set_state(ProcessingStates.waiting_for_clarification)

        else:
            await processing_msg.edit_text(
                f"❌ 处理失败\n\n{result.error or '请重新表述您的意思。'}"
            )

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        await processing_msg.edit_text(f"💥 发生错误\n\n错误信息: {str(e)}")


@dp.callback_query(F.data == "confirm")
async def confirm_data(query: CallbackQuery, state: FSMContext):
    """用户确认提取的数据 → 委托 MessageProcessor 写库。"""
    try:
        await query.message.edit_text("⏳ 正在保存到数据库...")

        fsm_data = await state.get_data()
        raw_text = fsm_data.get("raw_text", "")

        # ── 多事件路径 ──────────────────────────────────────────────────
        pending_events_raw = fsm_data.get("pending_events")
        if pending_events_raw:
            saved, failed = 0, 0
            for ev in pending_events_raw:
                ok = await processor.confirm(ev["skill_name"], ev["data"], raw_text)
                if ok:
                    saved += 1
                else:
                    failed += 1
            if failed == 0:
                await query.message.edit_text(f"✅ 已保存 {saved} 个事项")
            else:
                await query.message.edit_text(
                    f"⚠️ {saved} 个事项保存成功，{failed} 个保存失败"
                )
            await state.clear()
            await query.answer()
            return

        # ── 单事件路径（向后兼容）──────────────────────────────────────
        skill_name = fsm_data.get("skill_name")
        extracted_data = fsm_data.get("extracted_data", {})

        if not skill_name:
            await query.message.edit_text("❌ 状态已过期，请重新输入")
            await state.clear()
            await query.answer()
            return

        success = await processor.confirm(skill_name, extracted_data, raw_text)
        if success:
            formatted = _format_extracted_data(extracted_data)
            await query.message.edit_text(f"✅ 已保存\n\n{formatted}")
        else:
            await query.message.edit_text("❌ 保存到数据库失败")

        await state.clear()

    except Exception as e:
        logger.error(f"Error confirming data: {e}", exc_info=True)
        await query.message.edit_text(f"💥 保存失败\n\n错误: {str(e)}")
        await state.clear()
    finally:
        await query.answer()


@dp.callback_query(F.data == "reject")
async def reject_data(query: CallbackQuery, state: FSMContext):
    """用户拒绝提取结果 → 清除状态。"""
    await query.message.edit_text("👆 已取消。请重新告诉我您的意思。")
    await state.clear()
    await query.answer()


@dp.message(StateFilter(ProcessingStates.waiting_for_clarification), F.text)
async def handle_clarification_reply(message: types.Message, state: FSMContext):
    """处理用户对追问的回答，创建提醒事件。"""
    processing_msg = await message.answer("⏳ 正在创建提醒...")

    try:
        fsm_data = await state.get_data()
        item = fsm_data.get("clarification_item", "")
        original_text = fsm_data.get("clarification_original_text", "")

        result = await processor.process_clarification(item, original_text, message.text)

        if result.result_type == "skill_pending":
            await state.update_data(
                skill_name=result.skill_name,
                extracted_data=result.extracted_data,
                raw_text=original_text,
            )
            formatted = _format_extracted_data(result.extracted_data)
            response_text = (
                f"✅ 提醒已创建\n\n"
                f"提取数据:\n{formatted}\n\n"
                f"请确认是否保存到数据库？"
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✅ 确认入库", callback_data="confirm"),
                InlineKeyboardButton(text="❌ 取消", callback_data="reject"),
            ]])
            await processing_msg.edit_text(response_text, reply_markup=keyboard)
            await state.set_state(ProcessingStates.waiting_for_confirmation)
        else:
            # 解析失败，保留 FSM 状态让用户重新描述，不 clear
            fsm_data2 = await state.get_data()
            item_name = fsm_data2.get("clarification_item", "该物品")
            await processing_msg.edit_text(
                f"没能理解时间，换种说法试试（例如：两三天、下周、周末）\n\n"
                f"「{item_name}」大概还能用多久？"
            )

    except Exception as e:
        logger.error(f"Error handling clarification reply: {e}", exc_info=True)
        await processing_msg.edit_text(f"💥 发生错误\n\n{str(e)}")
        await state.clear()


def _format_extracted_data(data: Dict[str, Any]) -> str:
    lines = []
    for key, value in data.items():
        if key not in ["raw_text", "notes"]:
            display_key = key.replace("_", " ").title()
            display_value = ", ".join(str(v) for v in value) if isinstance(value, list) else str(value)
            lines.append(f"• {display_key}: {display_value}")
    if "notes" in data and data["notes"]:
        lines.append(f"• 备注: {data['notes']}")
    return "\n".join(lines) if lines else "无数据"

# ─── 每日提醒调度器 ────────────────────────────────────────────────────


async def send_daily_reminder():
    """每天早上 8 点推送当日日程提醒。"""
    if not TELEGRAM_CHAT_ID:
        logger.warning("TELEGRAM_CHAT_ID not set, skipping daily reminder")
        return
    try:
        text = await processor.generate_daily_reminder()
        if text:
            await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"🌅 早上好！\n\n{text}")
            logger.info("Daily reminder sent")
    except Exception as e:
        logger.error(f"Error sending daily reminder: {e}")


async def send_weekly_preview():
    """每周日晚 9 点推送下周日程预告。"""
    if not TELEGRAM_CHAT_ID:
        logger.warning("TELEGRAM_CHAT_ID not set, skipping weekly preview")
        return
    try:
        text = await processor.generate_weekly_preview()
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"📅 {text}")
        logger.info("Weekly preview sent")
    except Exception as e:
        logger.error(f"Error sending weekly preview: {e}")


def setup_scheduler() -> AsyncIOScheduler:
    """配置并返回调度器（不启动）。"""
    import pytz
    tz_name = os.getenv("TZ", "Asia/Shanghai")
    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        tz = pytz.utc

    scheduler = AsyncIOScheduler(timezone=tz)
    scheduler.add_job(send_daily_reminder, CronTrigger(hour=8, minute=0, timezone=tz))
    scheduler.add_job(send_weekly_preview, CronTrigger(day_of_week="sun", hour=21, minute=0, timezone=tz))
    return scheduler


async def main():
    """主程序。"""
    await startup_check()

    scheduler = setup_scheduler()
    scheduler.start()
    logger.info("✅ Scheduler started (daily 08:00, weekly Sun 21:00)")

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Webhook deleted, start long polling")

    logger.info("🤖 Bot is running...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error in polling loop: {str(e)}")
    finally:
        scheduler.shutdown(wait=False)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

