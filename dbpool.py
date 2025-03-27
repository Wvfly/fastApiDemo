## MySQL异步连接池

import asyncio,aiomysql,json
from typing import Optional, Dict
from datetime import datetime

conf="config/db.conf"
with open(conf) as cf:
    confmidd = json.loads(cf.read())
    host = confmidd["mysql_host"]
    port = confmidd["mysql_port"]
    user = confmidd["mysql_user"]
    password = confmidd["mysql_password"]
    db = confmidd["mysql_db"]
    minsize = confmidd["mysql_min_size"]
    maxsize = confmidd["mysql_max_size"]
    timeout = confmidd["mysql_timeout"]
    heartbeat_interval = confmidd["heartbeat_interval"]



class AsyncMySQLPool:
    def __init__(self):
        self.config = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "db": db,
            "minsize": minsize,
            "maxsize": maxsize,
            "charset": "utf8",
            "autocommit": True,
            "pool_recycle": heartbeat_interval - 30
        }
        self.pool: Optional[aiomysql.Pool] = None
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        self.pool = await aiomysql.create_pool(**self.config)
        self.heartbeat_task = asyncio.create_task(self._run_heartbeat())

    async def close(self) -> None:
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass

        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()

    async def _get_connection(self) -> aiomysql.Connection:
        """使用async with自动管理连接"""
        async with self.pool.acquire() as conn:
            try:
                await conn.ping(reconnect=True)  # 自动重连
            except aiomysql.OperationalError:
                await conn.ping(reconnect=True)
            return conn

    async def _run_heartbeat(self) -> None:
        """改进的心跳检查，自动释放资源"""
        while True:
            print(f"[{datetime.now()}] Running heartbeat check...")
            try:
                async with self.pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute("SELECT 1")
                        result = await cursor.fetchone()
                        if result != (1,):
                            raise ConnectionError("Heartbeat failed")
            except Exception as e:
                print(f"Heartbeat error: {e}")
            await asyncio.sleep(self.heartbeat_interval)

    async def execute(self, query: str, args: Optional[Dict] = None) -> int:
        """自动重试和连接管理"""
        for attempt in range(3):
            try:
                async with self.pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute(query, args)
                        return cursor.rowcount
            except aiomysql.OperationalError as e:
                if attempt == 2:
                    raise
                print(f"Retrying... ({attempt + 1}/3)")
                await asyncio.sleep(1)

    async def fetch_all(self, query: str, args: Optional[Dict] = None) -> list:
        """使用正确的上下文管理"""
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, args)
                return await cursor.fetchall()

    def pool_status(self) -> dict:
        if not self.pool:
            return {}
        return {
            "size": self.pool.size,
            "free": self.pool.freesize,
            "min": self.pool.minsize,
            "max": self.pool.maxsize
        }

