#!/usr/bin/env python3
"""
Ollama 客户端
与本地 Ollama 服务通信
"""

import httpx
import json
import logging
import os
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class OllamaClient:
    """
    Ollama 客户端
    
    用于与本地 Ollama 服务通信，进行文本生成和意图识别
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen:7b-chat"):
        """
        初始化 Ollama 客户端
        
        Args:
            base_url: Ollama 服务地址
            model: 使用的模型名称
        """
        self.base_url = base_url
        # 允许通过环境变量覆盖默认模型，便于不同环境快速切换。
        self.model = os.getenv("OLLAMA_MODEL", model)
        self.timeout = 120  # 120 秒超时
        
        logger.info(f"Initialized OllamaClient: {base_url}, model: {model}")
    
    async def generate(
        self,
        prompt: str,
        stream: bool = False,
        system: Optional[str] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> str:
        """
        生成文本
        
        Args:
            prompt: 输入 Prompt
            stream: 是否流式输出
            system: 系统 Prompt
            temperature: 温度参数（0-1）
            top_p: top_p 参数
            
        Returns:
            str: 生成的文本
        """
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": stream,
                "temperature": temperature,
                "top_p": top_p,
            }
            
            if system:
                payload["system"] = system
            
            logger.debug(f"Sending request to Ollama: model={self.model}, prompt_len={len(prompt)}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                
                if response.status_code != 200:
                    error_msg = f"Ollama error ({response.status_code}): {response.text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)
                
                if stream:
                    # 流式响应
                    text = ""
                    async for line in response.aiter_lines():
                        if line:
                            data = json.loads(line)
                            text += data.get("response", "")
                    return text
                else:
                    # 非流式响应
                    data = response.json()
                    return data.get("response", "")
        
        except httpx.TimeoutException:
            error_msg = f"Ollama request timeout after {self.timeout} seconds"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"Error calling Ollama: {str(e)}")
            raise
    
    async def skill_router(self, user_input: str) -> str:
        """
        技能路由：确定用户输入应该使用哪个技能
        
        这是第一层 LLM 调用，用于从预定义的技能列表中选择最合适的
        
        Args:
            user_input: 用户输入文本
            
        Returns:
            str: 选择的技能名称
        """
        from .skills import list_skills
        
        skills = list_skills()
        skills_desc = {
            'record_event': '记录一次性事件（理发、购物、烹饪等）',
            'schedule_event': '计划周期性或未来事件（课程、活动、医生预约等）',
        }
        
        skills_text = "\n".join([f"- {s}: {skills_desc.get(s, '')}" for s in skills])
        
        prompt = f"""你是一个意图识别助手。
根据用户的输入，从以下技能中选择最匹配的一个。

可用技能：
{skills_text}

用户输入："{user_input}"

请返回最匹配的技能名称。仅返回技能名称，不要有其他文字。
不要包含引号或其他符号，直接返回技能名称，例如：record_event 或 schedule_event"""
        
        try:
            result = await self.generate(
                prompt=prompt,
                stream=False,
                temperature=0.3  # 路由应该更确定
            )
            
            skill_name = result.strip().lower()
            
            # 验证返回的技能名称
            if skill_name in skills:
                logger.info(f"Skill router selected: {skill_name}")
                return skill_name
            else:
                logger.warning(f"Skill router returned unknown skill: {skill_name}, defaulting to record_event")
                return "record_event"  # 默认返回 record_event
        
        except Exception as e:
            logger.error(f"Error in skill router: {str(e)}")
            return "record_event"  # 发生错误时默认返回 record_event
    
    async def health_check(self) -> bool:
        """
        检查 Ollama 服务是否正常
        
        Returns:
            bool: 服务是否正常
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {str(e)}")
            return False
