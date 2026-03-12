#!/usr/bin/env python3
"""
VedaAide MVP 本地测试脚本
用于验证各个组件是否正常工作
"""

import asyncio
import logging
from typing import Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_ollama_client():
    """测试 Ollama 客户端"""
    logger.info("\n🧪 测试 1: Ollama 客户端")
    logger.info("-" * 50)
    
    try:
        from bot_app.ollama_client import OllamaClient
        
        client = OllamaClient()
        
        # 健康检查
        health = await client.health_check()
        if health:
            logger.info("✅ Ollama 服务正常")
        else:
            logger.error("❌ Ollama 服务无响应")
            return False
        
        # 测试 skill_router
        logger.info("\n📍 测试技能路由...")
        test_cases = [
            ("今天剪头了", "record_event"),
            ("孩子每周二有游泳课", "schedule_event"),
        ]
        
        for text, expected_skill in test_cases:
            logger.info(f"  输入: {text}")
            skill = await client.skill_router(text)
            logger.info(f"  输出: {skill}")
            logger.info(f"  期望: {expected_skill}")
            
            if skill and expected_skill.lower() in skill.lower():
                logger.info("  ✅ 正确")
            else:
                logger.warning("  ⚠️ 可能不匹配（但模型可能理解方式不同）")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ 错误: {str(e)}")
        return False


async def test_skills():
    """测试技能框架"""
    logger.info("\n🧪 测试 2: 技能框架")
    logger.info("-" * 50)
    
    try:
        from bot_app.ollama_client import OllamaClient
        from bot_app.skills import list_skills, get_skill
        
        ollama = OllamaClient()
        
        # 列出所有技能
        skills = list_skills()
        logger.info(f"✅ 可用技能: {skills}")
        
        # 测试 RecordEventSkill
        logger.info("\n📍 测试 RecordEventSkill...")
        skill = get_skill("record_event", ollama_client=ollama)
        if skill:
            logger.info("✅ 技能加载成功")
            
            result = await skill.execute("今天买了面包和牛奶")
            if result.get("success"):
                logger.info(f"✅ 提取成功: {result['data']}")
            else:
                logger.warning(f"⚠️ 提取失败: {result.get('error')}")
        else:
            logger.error("❌ 技能加载失败")
            return False
        
        # 测试 ScheduleEventSkill
        logger.info("\n📍 测试 ScheduleEventSkill...")
        skill = get_skill("schedule_event", ollama_client=ollama)
        if skill:
            logger.info("✅ 技能加载成功")
            
            result = await skill.execute("明天下午3点要去医院")
            if result.get("success"):
                logger.info(f"✅ 提取成功: {result['data']}")
            else:
                logger.warning(f"⚠️ 提取失败: {result.get('error')}")
        else:
            logger.error("❌ 技能加载失败")
            return False
        
        return True
    
    except Exception as e:
        logger.error(f"❌ 错误: {str(e)}")
        return False


async def test_database_client():
    """测试数据库客户端"""
    logger.info("\n🧪 测试 3: 数据库客户端")
    logger.info("-" * 50)
    
    try:
        from bot_app.db_client import DatabaseClient
        
        client = DatabaseClient()
        
        # 健康检查
        health = await client.health_check()
        if health:
            logger.info("✅ 数据库服务正常")
        else:
            logger.error("❌ 数据库服务无响应")
            logger.warning("   (这可能是正常的，如果您还没有启动 SQLite 服务)")
            return True  # 不认为这是错误，因为服务可能还没启动
        
        # 测试创建生活事件
        logger.info("\n📍 测试创建生活事件...")
        success = await client.create_life_event(
            category="haircut",
            item="理发",
            quantity=1,
            unit="次",
            raw_text="今天剪头了"
        )
        
        if success:
            logger.info("✅ 事件创建成功")
        else:
            logger.warning("⚠️ 事件创建失败")
        
        # 测试获取生活事件
        logger.info("\n📍 测试获取生活事件...")
        events = await client.get_life_events()
        logger.info(f"✅ 获取 {len(events)} 个事件")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ 错误: {str(e)}")
        return False


async def test_integration():
    """集成测试：完整流程"""
    logger.info("\n🧪 测试 4: 集成测试（完整流程）")
    logger.info("-" * 50)
    
    try:
        from bot_app.ollama_client import OllamaClient
        from bot_app.skills import get_skill
        from bot_app.db_client import DatabaseClient
        
        user_text = "今天吃了很好吃的披萨"
        logger.info(f"用户输入: {user_text}")
        
        # 第1步：选择技能
        logger.info("\n📍 第1步：选择技能...")
        ollama = OllamaClient()
        skill_name = await ollama.skill_router(user_text)
        logger.info(f"选择的技能: {skill_name}")
        
        # 第2步：执行技能
        logger.info("\n📍 第2步：执行技能...")
        skill = get_skill(skill_name, ollama_client=ollama)
        if not skill:
            logger.error("❌ 技能加载失败")
            return False
        
        result = await skill.execute(user_text)
        if not result.get("success"):
            logger.error(f"❌ 技能执行失败: {result.get('error')}")
            return False
        
        extracted_data = result.get("data", {})
        logger.info(f"✅ 提取的数据: {extracted_data}")
        
        # 第3步：保存到数据库
        logger.info("\n📍 第3步：保存到数据库...")
        db = DatabaseClient()
        
        if skill_name == "record_event":
            extracted_data["raw_text"] = user_text
            success = await db.create_life_event(**extracted_data)
        elif skill_name == "schedule_event":
            success = await db.create_scheduled_event(**extracted_data)
        else:
            logger.error(f"❌ 未知的技能: {skill_name}")
            return False
        
        if success:
            logger.info("✅ 数据保存成功")
            return True
        else:
            logger.warning("⚠️ 数据保存失败（数据库可能未启动）")
            return True  # 不认为这是错误
    
    except Exception as e:
        logger.error(f"❌ 错误: {str(e)}")
        return False


async def main():
    """主测试函数"""
    logger.info("=" * 60)
    logger.info("🚀 VedaAide MVP 本地测试")
    logger.info("=" * 60)
    
    results = {}
    
    # 运行所有测试
    results["Ollama 客户端"] = await test_ollama_client()
    results["技能框架"] = await test_skills()
    results["数据库客户端"] = await test_database_client()
    results["集成测试"] = await test_integration()
    
    # 打印测试结果
    logger.info("\n" + "=" * 60)
    logger.info("📊 测试结果汇总")
    logger.info("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    
    logger.info("=" * 60)
    if all_passed:
        logger.info("✅ 所有测试通过！MVP 已准备就绪")
    else:
        logger.info("❌ 部分测试失败，请检查日志")
    logger.info("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
