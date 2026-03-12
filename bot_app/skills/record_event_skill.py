#!/usr/bin/env python3
"""
记录事件技能 (RecordEventSkill)
用于记录一次性事件，如：理发、购物、烹饪消耗等
"""

from typing import Dict, Any, Optional
import json
import re
import logging
from .base_skill import BaseSkill

logger = logging.getLogger(__name__)


class RecordEventSkill(BaseSkill):
    """
    记录一次性事件的技能
    
    示例输入：
    - "今天剪头了"
    - "在 Woolworths 买了 2kg 牛肉"  
    - "今天用了 3 个鸡蛋烹饪"
    
    提取字段：
    - category: 事件类别 (haircut, grocery, cooking, etc.)
    - person: 相关人员（如 Marco / self）
    - location: 地点
    - item: 具体项目
    - quantity: 数量
    - unit: 单位
    - notes: 备注
    """
    
    def get_name(self) -> str:
        return "record_event"
    
    def get_description(self) -> str:
        return "记录一次性事件"
    
    def get_prompt(self) -> str:
        """
        高度优化的 Prompt，专注于提取事件信息
        """
        return """你是一个生活事件记录助手。
你的任务是从用户的自然语言描述中提取结构化的事件信息。

请从用户输入中提取以下信息，并返回严格的 JSON 格式（无其他文本）：
{
    "category": "事件类别，例如: haircut(理发), grocery(购物), cooking_use(烹饪消耗), entertainment(娱乐), health(健康), other",
    "person": "相关人员，例如: Marco, self, null",
    "location": "地点，例如: Woolworths, null",
    "item": "具体项目名称",
    "quantity": 数量（如果没有则为 null），
    "unit": "单位，例如: kg, 个, 次, 根, 片, etc",
    "notes": "其他备注或描述"
}

重要规则：
1. 如果用户提到的是"吃了N个XXX"，category 应该是 "consumption"（消费）
2. 如果是"买了XXX"，category 应该是 "grocery"（购物）
3. 理发相关用 "haircut"
4. 健康相关用 "health"
5. 如果信息不明确，尽量推测，但要确保返回有效的 JSON
6. 严格返回 JSON，不要有任何其他说明文字

示例：
- 用户: "今天剪头了"
  返回: {"category":"haircut","item":"理发","quantity":1,"unit":"次","notes":""}
  
- 用户: "在超市买了2kg牛肉"
  返回: {"category":"grocery","item":"牛肉","quantity":2,"unit":"kg","notes":"在超市购买"}
  
- 用户: "今天吃了5个饺子"
  返回: {"category":"consumption","item":"饺子","quantity":5,"unit":"个","notes":""}"""
    
    def parse_result(self, text: str) -> Optional[Dict[str, Any]]:
        """
        从 Ollama 输出中解析 JSON
        
        Args:
            text: Ollama 返回的文本
            
        Returns:
            Optional[Dict]: 解析的 JSON，或 None
        """
        try:
            # 移除可能的前后空白，并修复 LLM 常见的结尾逗号问题
            text = text.strip()
            text = re.sub(r',\s*([}\]])', r'\1', text)

            # 尝试找到 JSON 块
            # 方法1：直接 JSON
            try:
                data = json.loads(text)
                return self._validate_schema(data)
            except json.JSONDecodeError:
                pass

            # 方法2：从 ```json...``` 代码块中提取
            json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL | re.IGNORECASE)
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                    return self._validate_schema(data)
                except json.JSONDecodeError:
                    pass

            # 方法3：寻找 { ... } 块
            brace_start = text.find('{')
            brace_end = text.rfind('}')
            if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
                try:
                    json_str = text[brace_start:brace_end + 1]
                    data = json.loads(json_str)
                    return self._validate_schema(data)
                except json.JSONDecodeError:
                    pass
            
            logger.warning(f"Failed to parse JSON from: {text[:100]}")
            return None
            
        except Exception as e:
            logger.error(f"Error parsing result: {str(e)}")
            return None
    
    def _validate_schema(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        验证提取的数据是否符合 Schema
        
        Args:
            data: 要验证的数据
            
        Returns:
            Optional[Dict]: 验证通过的数据，或 None
        """
        required_fields = ['category', 'item']
        
        # 检查必需字段
        for field in required_fields:
            if field not in data or not data[field]:
                logger.warning(f"Missing required field: {field}")
                return None
        
        # 确保 quantity 是数字或 null
        if 'quantity' in data and data['quantity'] is not None:
            try:
                data['quantity'] = float(data['quantity'])
            except (ValueError, TypeError):
                data['quantity'] = None

        # person 是可选字段，保持 None 或字符串
        if 'person' in data and data['person'] is not None:
            data['person'] = str(data['person']).strip() or None
        
        return data
    
    async def save_to_db(self, data: Dict[str, Any]) -> bool:
        """
        将事件数据保存到数据库
        
        Args:
            data: 提取的事件数据
            
        Returns:
            bool: 是否保存成功
        """
        if not self.db_client:
            logger.warning("Database client not initialized")
            return False
        
        try:
            # 调用数据库 API
            response = await self.db_client.post(
                '/api/life_events',
                json={
                    'category': data.get('category'),
                    'person': data.get('person'),
                    'location': data.get('location'),
                    'item': data.get('item'),
                    'quantity': data.get('quantity'),
                    'unit': data.get('unit', ''),
                    'notes': data.get('notes', ''),
                    'raw_text': data.get('raw_text', '')
                }
            )
            
            if response.status_code == 201:
                logger.info(f"Successfully saved event to database: {data}")
                return True
            else:
                logger.error(f"Failed to save event: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error saving event to database: {str(e)}")
            return False
