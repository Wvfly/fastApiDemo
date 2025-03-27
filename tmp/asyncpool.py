from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic_settings import BaseSettings
import aiomysql
from aiomysql import Pool, DictCursor

# --- 配置管理 ---
class Settings(BaseSettings):
    mysql_host: str = "10.74.134.135"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = "123456@"
    mysql_db: str = "test"
    mysql_min_size: int = 5
    mysql_max_size: int = 20

settings = Settings()

# --- 数据库连接池生命周期管理 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 创建连接池
    app.state.mysql_pool = await aiomysql.create_pool(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        db=settings.mysql_db,
        minsize=settings.mysql_min_size,
        maxsize=settings.mysql_max_size,
        pool_recycle=3600,
        autocommit=False,
        # echo = True
    )
    yield
    # 关闭连接池
    app.state.mysql_pool.close()
    await app.state.mysql_pool.wait_closed()

app = FastAPI(lifespan=lifespan)

# --- 依赖注入 ---
async def get_db_pool() -> Pool:
    return app.state.mysql_pool

async def get_connection(pool: Pool = Depends(get_db_pool)) -> aiomysql.Connection:
    async with pool.acquire() as conn:
        yield conn

async def get_cursor(conn: aiomysql.Connection = Depends(get_connection)) -> DictCursor:
    async with conn.cursor(DictCursor) as cursor:
        yield cursor


# --- 路由示例 ---
# @app.get("/users/{user_id}")
@app.get("/users")
async def get_user(
    # user_id: int,
    cursor: DictCursor = Depends(get_cursor)
):
    try:
        await cursor.execute(
            "show databases"
        )
        msg = await cursor.fetchall()
        # print(msg)
        if not msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="msg not found"
            )
        return msg
    except aiomysql.Error as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

# @app.post("/users")
# async def create_user(
#     username: str,
#     email: str,
#     conn: aiomysql.Connection = Depends(get_connection),
#     cursor: DictCursor = Depends(get_cursor)
# ):
#     try:
#         async with conn.begin():  # 显式事务管理
#             await cursor.execute(
#                 "INSERT INTO users (username, email) VALUES (%s, %s)",
#                 (username, email)
#             )
#             await cursor.execute("SELECT LAST_INSERT_ID() AS id")
#             result = await cursor.fetchone()
#             return {"id": result["id"], "username": username, "email": email}
#     except aiomysql.IntegrityError as e:
#         raise HTTPException(
#             status_code=status.HTTP_409_CONFLICT,
#             detail=f"Duplicate entry: {str(e)}"
#         )
#     except aiomysql.Error as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Database error: {str(e)}"
#         )

# --- 错误处理中间件 ---
# @app.middleware("http")
# async def db_connection_middleware(request, call_next):
#     try:
#         return await call_next(request)
#     except aiomysql.OperationalError as e:
#         raise HTTPException(
#             status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
#             detail=f"Database connection failed: {str(e)}"
#         )

# --- 运行命令 ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
