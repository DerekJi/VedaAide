"""
VedaAide Skills 模块
"""

from .base_skill import BaseSkill
from .record_event_skill import RecordEventSkill
from .schedule_event_skill import ScheduleEventSkill

__all__ = [
    'BaseSkill',
    'RecordEventSkill',
    'ScheduleEventSkill',
]

# 技能注册表
SKILLS = {
    'record_event': RecordEventSkill,
    'schedule_event': ScheduleEventSkill,
}


def get_skill(skill_name: str, ollama_client=None, db_client=None) -> BaseSkill:
    """
    获取技能实例
    
    Args:
        skill_name: 技能名称
        ollama_client: Ollama 客户端
        db_client: 数据库客户端
        
    Returns:
        BaseSkill: 技能实例
        
    Raises:
        ValueError: 技能不存在
    """
    if skill_name not in SKILLS:
        raise ValueError(f"Unknown skill: {skill_name}")
    
    return SKILLS[skill_name](ollama_client=ollama_client, db_client=db_client)


def list_skills() -> list:
    """
    列出所有可用的技能
    
    Returns:
        list: 技能名称列表
    """
    return list(SKILLS.keys())
