#!/usr/bin/env python3
"""
VedaAide Telegram 机器人
主程序入口
"""

import os
import json
import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio
from dotenv import load_dotenv

from bot_app.ollama_client import OllamaClient
from bot_app.skills import get_skill
from bot_app.db_client import DatabaseClient

PROFILE_RECOMMENDED_KEYS = {
    "self_name",
    "self_birthday",
    "self_birth_place",
    "self_gender",
    "immigration_year",
    "immigration_country",
    "current_city",
    "son_name",
    "son_birthday",
    "daughter_name",
    "daughter_birthday",
}

PROFILE_KEY_ALIASES = {
    "name": "self_name",
    "birthday": "self_birthday",
    "birth_place": "self_birth_place",
    "gender": "self_gender",
    "country": "immigration_country",
    "city": "current_city",
    "son_birthdate": "son_birthday",
    "daughter_birthdate": "daughter_birthday",
}

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
OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
DB_BASE_URL = os.getenv("DB_URL", "http://localhost:5000")

if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN environment variable not set!")

# 初始化客户端
bot = Bot(token=TELEGRAM_TOKEN)
ollama_client = OllamaClient(base_url=OLLAMA_BASE_URL)
db_client = DatabaseClient(base_url=DB_BASE_URL)
dp = Dispatcher()

# FSM 状态定义
class ProcessingStates(StatesGroup):
    """处理状态机"""
    waiting_for_confirmation = State()  # 等待用户确认技能提取的数据


# 全局状态存储 - 用于保存临时处理数据
processing_state: Dict[int, Dict[str, Any]] = {}


async def startup_check():
    """
    启动检查
    验证所有依赖服务是否正常
    """
    logger.info("🚀 Starting VedaAide bot...")
    
    # 检查 Ollama
    if await ollama_client.health_check():
        logger.info("✅ Ollama service is running")
    else:
        logger.warning("⚠️ Ollama service is not available")
    
    # 检查数据库
    if await db_client.health_check():
        logger.info("✅ Database service is running")
    else:
        logger.warning("⚠️ Database service is not available")


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


async def _extract_background_updates(text: str) -> Dict[str, Any]:
    """使用 LLM 从自然语言中提取背景信息 - 自适应、鲁棒、易维护。"""
    recommended_keys = "\n".join(f"  - {k}" for k in sorted(PROFILE_RECOMMENDED_KEYS))
    prompt = f"""从用户输入中提取个人背景信息，以 JSON 格式返回。

推荐优先使用以下标准键名（英文 snake_case）：
{recommended_keys}

如果用户提到新的背景字段（例如爱好、职业、学校），允许输出新的英文 snake_case 键名。
关系语义必须准确：
- 本人信息使用 self_*（例如 self_birthday）
- 儿子信息使用 son_*（例如 son_birthday）
- 女儿信息使用 daughter_*（例如 daughter_birthday）

格式要求：
- 日期统一为 YYYY-MM-DD（例如 1978-01-16）
- 年份字段为纯数字字符串（例如 "2010"）
- 未提及的字段不要包含
- 只返回 JSON 对象本身，禁止任何解释文字

示例输入：我叫吉治钢，1978年1月16号出生于河南郑州，男
示例输出：{{"self_name":"吉治钢","self_birthday":"1978-01-16","self_birth_place":"河南郑州","self_gender":"男"}}

用户输入：{text}"""

    system_prompt = (
        "你是结构化信息提取器。"
        "只输出单个 JSON 对象。"
        "键名必须是英文 snake_case。"
        "关系语义要准确，不要把女儿信息写到 self_*。"
        "不输出任何解释。"
    )

    try:
        result = await ollama_client.generate(
            prompt=prompt,
            stream=False,
            system=system_prompt,
            temperature=0.1,  # 低温度确保提取准确
            top_p=0.3,
        )
        logger.info(f"LLM profile raw output: {result[:200]}")

        # 解析 JSON
        parsed = _parse_json_safely(result)
        if not parsed:
            # 二次重试：进一步压缩输出自由度
            retry_prompt = (
                "仅返回 JSON 对象，不要输出任何解释。\n"
                f"用户输入：{text}"
            )
            retry_result = await ollama_client.generate(
                prompt=retry_prompt,
                stream=False,
                system=system_prompt,
                temperature=0.0,
                top_p=0.1,
            )
            logger.info(f"LLM profile retry output: {retry_result[:200]}")
            parsed = _parse_json_safely(retry_result)

        if parsed:
            normalized = _normalize_profile_updates(parsed)
            if normalized:
                return normalized
        return {}

    except Exception as e:
        logger.error(f"Error extracting background info with LLM: {str(e)}")
        return {}


def _normalize_profile_updates(updates: Dict[str, Any], profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """规范化背景信息字段：优先映射标准键名，允许安全扩展键。"""
    normalized: Dict[str, Any] = {}
    for key, value in (updates or {}).items():
        mapped_key = _normalize_profile_key(key)
        if not mapped_key:
            logger.info(f"Profile key dropped (invalid): {key!r}")
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
    """将原始键名归一化为安全的 snake_case，并映射常见别名。"""
    if not isinstance(key, str):
        return None

    candidate = key.strip().lower()
    if not candidate:
        return None

    candidate = PROFILE_KEY_ALIASES.get(candidate, candidate)
    candidate = re.sub(r"[^a-z0-9_]+", "_", candidate)
    candidate = re.sub(r"_+", "_", candidate).strip("_")

    if not re.match(r"^[a-z][a-z0-9_]*$", candidate):
        return None
    return candidate


def _parse_json_safely(text: str) -> Optional[Dict[str, Any]]:
    """安全解析 JSON，处理 LLM 输出中的常见问题。"""
    if not text:
        return None

    candidate = text.strip()
    if not candidate:
        return None

    # 第一次尝试直接解析
    try:
        data = json.loads(candidate)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass

    # 清理常见问题：代码块、智能引号、结尾逗号、截断未闭合
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", candidate, flags=re.IGNORECASE)
    if fenced:
        candidate = fenced.group(1).strip()

    candidate = candidate.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    candidate = re.sub(r',\s*([}\]])', r'\1', candidate)
    # 清理被截断造成的残缺键，例如："子女_名字":
    candidate = re.sub(r',?\s*"[^"\n]+"\s*:\s*$', '', candidate)

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
        # 使用 JSONDecoder 扫描文本中第一个合法 JSON 对象
        decoder = json.JSONDecoder()
        for idx, ch in enumerate(candidate):
            if ch != '{':
                continue
            try:
                data, _ = decoder.raw_decode(candidate[idx:])
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                continue
        logger.warning(f"Failed to parse JSON: {text[:100]}")
        return None


def _looks_like_profile_text(text: str) -> bool:
    """粗粒度判断是否属于背景资料描述，避免误路由到事件技能。"""
    profile_markers = [
        "我叫", "我是", "儿子", "女儿", "生日", "出生", "出生于", "男", "女",
        "移民", "住在", "一直在", "来自", "国籍"
    ]
    return any(m in text for m in profile_markers)


@dp.message(StateFilter(None), F.text)
async def process_user_message(message: types.Message, state: FSMContext):
    """
    处理用户消息
    
    流程：
    1. 使用 Ollama 选择合适的 Skill
    2. 执行 Skill 提取结构化数据
    3. 显示提取结果给用户确认
    4. 等待用户确认或修改
    """
    user_id = message.from_user.id
    
    # 显示处理中的消息
    processing_msg = await message.answer("⏳ 正在处理您的消息...")
    
    try:
        # 优先处理背景知识更新
        profile_updates = await _extract_background_updates(message.text)
        if profile_updates:
            existing_profile = await db_client.get_user_profile()
            profile_updates = _normalize_profile_updates(profile_updates, existing_profile)

            ok = await db_client.update_user_profile(profile_updates)
            if ok:
                lines = ["✅ 背景信息已更新："]
                for k, v in profile_updates.items():
                    lines.append(f"• {k}: {v}")
                await processing_msg.edit_text("\n".join(lines))
            else:
                await processing_msg.edit_text("❌ 背景信息保存失败，请稍后重试")
            return

        # 背景语义但未提取到结构化字段时，避免错误走 event 技能
        if _looks_like_profile_text(message.text):
            await processing_msg.edit_text(
                "📝 看起来你在更新背景信息，但我还没提取到结构化字段。\n"
                "可以按下面格式再说一次：\n"
                "• 我叫张三，1988年6月1号出生于上海，男\n"
                "• 我儿子叫Marco，他的生日是2014年5月29号"
            )
            return

        # 第1步：使用 Ollama 的 skill_router 选择技能
        logger.info(f"[User {user_id}] Processing: {message.text}")
        
        selected_skill_name = await ollama_client.skill_router(message.text)
        logger.info(f"[User {user_id}] Selected skill: {selected_skill_name}")
        
        if selected_skill_name is None:
            await processing_msg.edit_text(
                "😅 抱歉，我不太理解您的意思。\n"
                "请尝试告诉我一些具体的事情或日程安排。\n\n"
                "例如：\n"
                "• 「今天剪头了」\n"
                "• 「周二有游泳课」"
            )
            return
        
        # 第2步：获取技能并执行
        skill = get_skill(
            selected_skill_name,
            ollama_client=ollama_client,
            db_client=db_client,
        )
        if not skill:
            await processing_msg.edit_text(
                f"❌ 技能加载失败: {selected_skill_name}"
            )
            logger.error(f"[User {user_id}] Skill not found: {selected_skill_name}")
            return
        
        # 执行技能 - 调用 Ollama 提取结构化数据
        result = await skill.execute(message.text)
        
        logger.info(f"[User {user_id}] Skill result: {result}")
        
        if result.get("success"):
            # 第3步：保存处理状态
            processing_state[user_id] = {
                "skill_name": selected_skill_name,
                "extracted_data": result.get("data", {}),
                "raw_text": message.text,
                "timestamp": datetime.now().isoformat()
            }
            
            # 第4步：格式化并显示提取结果
            extracted_data = result.get("data", {})
            formatted_text = _format_extracted_data(extracted_data)
            
            response_text = (
                f"✅ 识别成功\n\n"
                f"**技能**: {selected_skill_name}\n\n"
                f"**提取数据**:\n{formatted_text}\n\n"
                f"请确认是否保存到数据库？"
            )
            
            # 创建确认按钮
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ 确认入库",
                        callback_data=f"confirm_{user_id}"
                    ),
                    InlineKeyboardButton(
                        text="❌ 重新识别",
                        callback_data=f"reject_{user_id}"
                    )
                ]
            ])
            
            # 编辑处理中的消息，显示结果
            await processing_msg.edit_text(response_text, reply_markup=keyboard)
            
            # 设置 FSM 状态为等待确认
            await state.set_state(ProcessingStates.waiting_for_confirmation)
            
        else:
            # 处理失败的情况
            error_msg = result.get("error", "处理出错")
            await processing_msg.edit_text(
                f"❌ 处理失败\n\n"
                f"错误: {error_msg}\n\n"
                f"请重新表述您的意思。"
            )
    
    except Exception as e:
        logger.error(f"[User {user_id}] Error processing message: {str(e)}", exc_info=True)
        await processing_msg.edit_text(
            f"💥 发生错误\n\n"
            f"错误信息: {str(e)}"
        )


@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_data(query: CallbackQuery, state: FSMContext):
    """
    用户确认提取的数据
    将数据保存到数据库
    """
    user_id = query.from_user.id
    
    try:
        # 重新编辑消息，表示处理中
        await query.message.edit_text("⏳ 正在保存到数据库...")
        
        # 获取处理状态
        if user_id not in processing_state:
            await query.message.edit_text("❌ 状态已过期，请重新输入")
            return
        
        state_data = processing_state[user_id]
        skill_name = state_data["skill_name"]
        extracted_data = state_data["extracted_data"]
        raw_text = state_data["raw_text"]
        
        logger.info(f"[User {user_id}] Confirming data for skill: {skill_name}")
        
        # 根据技能类型保存数据
        success = False
        
        if skill_name == "record_event":
            # 保存生活事件
            extracted_data["raw_text"] = raw_text
            success = await db_client.create_life_event(**extracted_data)
            
            if success:
                response = (
                    "✅ 数据已保存到数据库\n\n"
                    f"人员: {extracted_data.get('person', 'N/A')}\n"
                    f"地点: {extracted_data.get('location', 'N/A')}\n"
                    f"事件类别: {extracted_data.get('category', 'N/A')}\n"
                    f"物品: {extracted_data.get('item', 'N/A')}\n"
                    f"数量: {extracted_data.get('quantity', 1)} {extracted_data.get('unit', '')}\n"
                )
            else:
                response = "❌ 保存到数据库失败"
        
        elif skill_name == "schedule_event":
            # 保存计划事件
            success = await db_client.create_scheduled_event(**extracted_data)
            
            if success:
                response = (
                    "✅ 计划已保存\n\n"
                    f"人员: {extracted_data.get('person', 'N/A')}\n"
                    f"地点: {extracted_data.get('location', 'N/A')}\n"
                    f"标题: {extracted_data.get('title', 'N/A')}\n"
                    f"开始时间: {extracted_data.get('start_time', 'N/A')}\n"
                    f"结束时间: {extracted_data.get('end_time', 'N/A')}\n"
                    f"重复规则: {extracted_data.get('recurrence_rule', '一次性')}\n"
                )
            else:
                response = "❌ 保存计划失败"
        
        else:
            response = f"❌ 未知的技能: {skill_name}"
        
        await query.message.edit_text(response)
        
        # 清理状态
        del processing_state[user_id]
        await state.clear()
        
    except Exception as e:
        logger.error(f"[User {user_id}] Error confirming data: {str(e)}", exc_info=True)
        await query.message.edit_text(
            f"💥 保存失败\n\n"
            f"错误: {str(e)}"
        )
        await state.clear()
    
    finally:
        # 删除回调查询应答
        await query.answer()


@dp.callback_query(F.data.startswith("reject_"))
async def reject_data(query: CallbackQuery, state: FSMContext):
    """
    用户拒绝提取的数据
    清除状态，等待重新输入
    """
    user_id = query.from_user.id
    
    # 清理状态
    if user_id in processing_state:
        del processing_state[user_id]
    
    await query.message.edit_text(
        "👆 已取消。请重新告诉我您的意思。"
    )
    
    await state.clear()
    await query.answer()


def _format_extracted_data(data: Dict[str, Any]) -> str:
    """
    格式化提取的数据以供显示
    """
    lines = []
    for key, value in data.items():
        if key not in ["raw_text", "notes"]:
            # 转换键名为可读形式
            display_key = key.replace("_", " ").title()
            
            # 处理值
            if isinstance(value, list):
                display_value = ", ".join(str(v) for v in value)
            else:
                display_value = str(value)
            
            lines.append(f"• {display_key}: {display_value}")
    
    # 如果有备注，添加到最后
    if "notes" in data and data["notes"]:
        lines.append(f"• 备注: {data['notes']}")
    
    return "\n".join(lines) if lines else "无数据"


async def main():
    """
    主程序
    """
    # 执行启动检查
    await startup_check()

    # 使用 long polling 前先删除 webhook，避免 TelegramConflictError
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Webhook deleted, start long polling")
    
    # 启动 polling
    logger.info("🤖 Bot is running...")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error in polling loop: {str(e)}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
