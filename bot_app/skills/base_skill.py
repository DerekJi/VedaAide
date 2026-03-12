#!/usr/bin/env python3
"""
VedaAide Skill 基类
所有技能都应继承此基类
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)


class BaseSkill(ABC):
    """
    技能基类
    
    所有 Skill 都应继承此类，并实现以下方法：
    - get_name(): 返回技能名称
    - get_prompt(): 返回给 Ollama 的 Prompt
    - execute(): 执行技能逻辑并返回结构化结果
    """
    
    def __init__(self, ollama_client=None, db_client=None):
        """
        初始化 Skill
        
        Args:
            ollama_client: Ollama 客户端
            db_client: 数据库客户端
        """
        self.ollama_client = ollama_client
        self.db_client = db_client
    
    @abstractmethod
    def get_name(self) -> str:
        """
        返回技能名称
        
        Returns:
            str: 技能名称，例如 "record_event"
        """
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """
        返回技能描述
        
        Returns:
            str: 技能描述
        """
        pass
    
    @abstractmethod
    def get_prompt(self) -> str:
        """
        返回给 Ollama 的系统 Prompt
        
        这个 Prompt 应该非常专注和简洁，用于指导 LLM
        执行特定任务并返回结构化JSON
        
        Returns:
            str: Prompt 文本
        """
        pass
    
    @abstractmethod
    def parse_result(self, text: str) -> Optional[Dict[str, Any]]:
        """
        从 Ollama 的输出中解析结构化数据
        
        Args:
            text: Ollama 返回的文本
            
        Returns:
            Optional[Dict]: 解析后的结构化数据，或 None 如果解析失败
        """
        pass
    
    async def execute(self, user_input: str) -> Dict[str, Any]:
        """
        执行技能
        
        步骤：
        1. 将用户输入发送给 Ollama
        2. 使用此技能的专用 Prompt
        3. 解析返回结果
        4. 返回结构化数据
        
        Args:
            user_input: 用户输入文本
            
        Returns:
            Dict: 包含以下字段的字典
                - success: bool - 执行是否成功
                - data: Optional[Dict] - 提取的结构化数据
                - message: str - 给用户的反馈消息
                - error: Optional[str] - 错误信息（如果有）
        """
        try:
            if not self.ollama_client:
                return {
                    'success': False,
                    'message': '❌ Ollama 客户端未初始化',
                    'error': 'ollama_client is None'
                }
            
            # 调用 Ollama
            logger.info(f"Executing {self.get_name()} with input: {user_input[:50]}...")
            
            response = await self.ollama_client.generate(
                prompt=f"{self.get_prompt()}\n\n用户输入：{user_input}",
                stream=False
            )
            
            # 解析结果
            parsed_data = self.parse_result(response)
            
            if parsed_data:
                logger.info(f"{self.get_name()} parsed successfully: {parsed_data}")
                return {
                    'success': True,
                    'data': parsed_data,
                    'message': f"✅ 已识别为：{self.get_description()}\n\n提取的信息：\n{self._format_data(parsed_data)}"
                }
            else:
                logger.warning(f"{self.get_name()} failed to parse: {response[:100]}")
                return {
                    'success': False,
                    'message': f"❌ 无法理解你的输入，请重试\n\nOllama 返回：{response[:100]}",
                    'error': 'parse_failed'
                }
                
        except Exception as e:
            logger.error(f"Error executing {self.get_name()}: {str(e)}")
            return {
                'success': False,
                'message': f"❌ 执行失败：{str(e)}",
                'error': str(e)
            }
    
    def _format_data(self, data: Dict[str, Any]) -> str:
        """
        将结构化数据格式化为易读的字符串
        
        Args:
            data: 结构化数据
            
        Returns:
            str: 格式化后的字符串
        """
        result = []
        for key, value in data.items():
            if value is not None:
                result.append(f"  • {key}: {value}")
        return "\n".join(result) if result else "（空）"
    
    def save_to_db(self, data: Dict[str, Any]) -> bool:
        """
        将数据保存到数据库
        
        子类可以覆盖此方法实现自定义保存逻辑
        
        Args:
            data: 要保存的数据
            
        Returns:
            bool: 是否保存成功
        """
        if not self.db_client:
            logger.warning("Database client not initialized")
            return False
        
        try:
            # 默认保存到 life_events 表
            # 子类应该覆盖此方法
            logger.info(f"Saving data to database: {data}")
            return True
        except Exception as e:
            logger.error(f"Error saving to database: {str(e)}")
            return False
