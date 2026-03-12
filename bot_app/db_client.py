#!/usr/bin/env python3
"""
数据库客户端
与 SQLite Web API 通信
"""

import httpx
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class DatabaseClient:
    """
    数据库客户端
    
    与 SQLite Web API 通信，执行数据库操作
    """
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        """
        初始化数据库客户端
        
        Args:
            base_url: SQLite Web API 服务地址
        """
        self.base_url = base_url
        self.timeout = 30
        
        logger.info(f"Initialized DatabaseClient: {base_url}")
    
    async def post(self, endpoint: str, json: Dict[str, Any]) -> "httpx.Response":
        """
        POST 请求
        
        Args:
            endpoint: API 端点
            json: 请求 JSON 数据
            
        Returns:
            httpx.Response: 响应对象
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.base_url}{endpoint}"
                logger.debug(f"POST {url}: {json}")
                
                response = await client.post(url, json=json)
                
                if response.status_code >= 400:
                    logger.error(f"Database API error ({response.status_code}): {response.text}")
                else:
                    logger.debug(f"Database API response: {response.status_code}")
                
                return response
        
        except Exception as e:
            logger.error(f"Error making POST request to database: {str(e)}")
            raise
    
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> "httpx.Response":
        """
        GET 请求
        
        Args:
            endpoint: API 端点
            params: 查询参数
            
        Returns:
            httpx.Response: 响应对象
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.base_url}{endpoint}"
                logger.debug(f"GET {url}: {params}")
                
                response = await client.get(url, params=params)
                
                if response.status_code >= 400:
                    logger.error(f"Database API error ({response.status_code}): {response.text}")
                else:
                    logger.debug(f"Database API response: {response.status_code}")
                
                return response
        
        except Exception as e:
            logger.error(f"Error making GET request to database: {str(e)}")
            raise
    
    # 便利方法 - 生活事件
    
    async def create_life_event(self, **kwargs) -> bool:
        """
        创建生活事件
        
        Args:
            **kwargs: 事件数据（category, item, quantity, unit, notes, raw_text）
            
        Returns:
            bool: 是否创建成功
        """
        try:
            response = await self.post('/api/life_events', json=kwargs)
            return response.status_code == 201
        except Exception as e:
            logger.error(f"Error creating life event: {str(e)}")
            return False
    
    async def get_life_events(self, limit: int = 50, offset: int = 0, category: Optional[str] = None) -> List[Dict]:
        """
        获取生活事件列表
        
        Args:
            limit: 限制数量
            offset: 偏移量
            category: 按类别过滤
            
        Returns:
            List[Dict]: 事件列表
        """
        try:
            params = {'limit': limit, 'offset': offset}
            if category:
                params['category'] = category
            
            response = await self.get('/api/life_events', params=params)
            data = response.json()
            return data.get('data', [])
        except Exception as e:
            logger.error(f"Error fetching life events: {str(e)}")
            return []
    
    # 便利方法 - 计划事件
    
    async def create_scheduled_event(self, **kwargs) -> bool:
        """
        创建计划事件
        
        Args:
            **kwargs: 事件数据（title, category, start_time, end_time, recurrence_rule, required_items, notes）
            
        Returns:
            bool: 是否创建成功
        """
        try:
            response = await self.post('/api/scheduled_events', json=kwargs)
            return response.status_code == 201
        except Exception as e:
            logger.error(f"Error creating scheduled event: {str(e)}")
            return False
    
    async def get_scheduled_events(self) -> List[Dict]:
        """
        获取计划事件列表
        
        Returns:
            List[Dict]: 事件列表
        """
        try:
            response = await self.get('/api/scheduled_events')
            data = response.json()
            return data.get('data', [])
        except Exception as e:
            logger.error(f"Error fetching scheduled events: {str(e)}")
            return []
    
    # 便利方法 - 用户背景信息
    
    async def update_user_profile(self, profile_data: Dict[str, Any]) -> bool:
        """
        更新用户背景信息
        
        Args:
            profile_data: 背景信息键值对
            
        Returns:
            bool: 是否更新成功
        """
        try:
            response = await self.post('/api/user_profile', json=profile_data)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error updating user profile: {str(e)}")
            return False
    
    async def get_user_profile(self) -> Dict[str, str]:
        """
        获取用户背景信息
        
        Returns:
            Dict[str, str]: 背景信息
        """
        try:
            response = await self.get('/api/user_profile')
            data = response.json()
            return data.get('data', {})
        except Exception as e:
            logger.error(f"Error fetching user profile: {str(e)}")
            return {}
    
    # 便利方法 - 健康检查
    
    async def health_check(self) -> bool:
        """
        检查数据库服务是否正常
        
        Returns:
            bool: 服务是否正常
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return False
