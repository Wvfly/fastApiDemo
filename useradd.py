## 调用封装好的异步mysql库

from fastapi import FastAPI,HTTPException,status
import asyncio
from dbpool import AsyncMySQLPool
from contextlib import asynccontextmanager

pool = AsyncMySQLPool(
    # host="10.74.134.135",
    # user="root",
    # password="123456@",
    # db="test",
    # heartbeat_interval=180
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化连接池，路由下面就不再需要初始化pool
    await pool.initialize()
    yield
    # 关闭时清理连接池
    await pool.close()

app = FastAPI(lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)

@app.get("/usersadd1")
async def useradd():
    try:
        await pool.fetch_all("SELECT SLEEP(9)")     #这个先执行，执行完再执行tasks中的两个

        tasks=[                                     #这两个并行执行
            pool.execute("SELECT SLEEP(10)"),
            pool.execute("SELECT SLEEP(8)")
        ]

        result = await asyncio.gather(*tasks)
        print(result)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No data found"
            )

        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=e
        )



if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
