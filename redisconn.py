## redis连接池

import aioredis,json
from aioredis import ConnectionPool
from typing import Optional
from contextlib import asynccontextmanager

conf="config/db.conf"
with open(conf) as cf:
    confmidd = json.loads(cf.read())
    host = confmidd["redis_host"]
    port = confmidd["redis_port"]
    password = confmidd["redis_password"]
    db = confmidd["redis_db"]
    redis_channel = confmidd["redis_channel"]
    redis_url = confmidd["redis_url"]


class RedisManager:
    def __init__(self):
        self._redis_pool: Optional[aioredis.Redis] = None
        # self._connections_in_use = 0  # 自定义计数器

    async def initialize(self):
        """异步初始化连接池"""
        if not self._redis_pool:
            self._redis_pool = await aioredis.from_url(
                redis_url,
                password=password,
                db=db,  # 添加缺失的db参数
                encoding="utf-8",
                max_connections=20,
                decode_responses=True
            )

    @asynccontextmanager
    async def get_connection(self):
        """获取连接的上下文管理器"""
        if not self._redis_pool:
            await self.initialize()

        async with self._redis_pool.client() as conn:
            yield conn

    def get_pool_stats(self,pool: ConnectionPool) -> dict:
        """获取连接池统计信息（兼容 aioredis 2.x+）"""
        return {
            "in_use": pool._in_use_connections.__str__(),  # 当前活跃连接数
            "free": pool._available_connections.__str__(),  # 空闲连接数
            "size": pool.max_connections  # 最大连接数
        }
    async def close(self):
        """正确关闭连接池"""
        if self._redis_pool:
            await self._redis_pool.close()
            await self._redis_pool.connection_pool.disconnect()
            self._redis_pool = None

    @property
    def channel(self):
        """订阅频道名称"""
        return redis_channel






