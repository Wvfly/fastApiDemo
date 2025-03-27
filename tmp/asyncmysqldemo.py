from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic_settings import BaseSettings, SettingsConfigDict
import aiomysql,json,asyncio
from aiomysql import Pool, DictCursor
from typing import Optional, AsyncGenerator


# --- 配置管理 ---
# class DatabaseSettings(BaseSettings):
#     mysql_host: str = "10.74.134.135"
#     mysql_port: int = 3306
#     mysql_user: str = "root"
#     mysql_password: str = "123456@"
#     mysql_db: str = "test"
#     mysql_min_size: int = 5
#     mysql_max_size: int = 20
#     mysql_timeout: int = 10  # 新增连接超时参数
#
#     # model_config = SettingsConfigDict(
#     #     env_file=".env",
#     #     env_file_encoding="utf-8",
#     #     env_prefix="MYSQL_"
#     # )
#
# settings = DatabaseSettings()
conf_file="config/db.conf"
with open(conf_file) as cf:
    settings=json.loads(cf.read())

# --- 生命周期管理 ---
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # 初始化连接池
    app.state.db_pool = await aiomysql.create_pool(
        # host=settings.mysql_host,
        # port=settings.mysql_port,
        # user=settings.mysql_user,
        # password=settings.mysql_password,
        # db=settings.mysql_db,
        # minsize=settings.mysql_min_size,
        # maxsize=settings.mysql_max_size,
        # pool_recycle=3600,
        # autocommit=False,
        # connect_timeout=settings.mysql_timeout,
        # cursorclass=DictCursor  # 使用字典游标
        host=settings["mysql_host"],
        port=settings["mysql_port"],
        user=settings["mysql_user"],
        password=settings["mysql_password"],
        db=settings["mysql_db"],
        minsize=settings["mysql_min_size"],
        maxsize=settings["mysql_max_size"],
        pool_recycle=3600,
        autocommit=False,
        connect_timeout=settings["mysql_timeout"],
        cursorclass=DictCursor  # 使用字典游标
    )
    yield
    # 关闭连接池
    app.state.db_pool.close()
    await app.state.db_pool.wait_closed()


app = FastAPI(lifespan=lifespan)
# settings = DatabaseSettings()


# --- 依赖注入 ---
async def get_db() -> AsyncGenerator[aiomysql.Connection, None]:
    async with app.state.db_pool.acquire() as conn:
        try:
            yield conn
        finally:
            # 自动归还连接时重置连接状态
            await conn.ping(True)


# --- 事务管理工具 ---
@asynccontextmanager
async def db_transaction(conn: aiomysql.Connection):
    try:
        await conn.begin()
        yield
        await conn.commit()
    except Exception as e:
        print(e)
        await conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transaction failed: {str(e)}"
        )


# --- sql执行器 ---
async def execute_sql(
        sql: str,
        params: Optional[tuple] = None,
        conn: aiomysql.Connection = Depends(get_db)
):
    print(sql)
    async with conn.cursor() as cur:
        try:
            await cur.execute(sql, params or ())
            if cur.description:  # 判断是否有返回结果
                return await cur.fetchall()
            return {"affected_rows": cur.rowcount}
        except aiomysql.Error as e:
            print(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Query execution error: {e.args}"
            ) from e


# --- 路由示例 ---
@app.get("/users")
async def get_databases(conn: aiomysql.Connection = Depends(get_db)):
    async with db_transaction(conn):
        result = await execute_sql("select * from userxxx", conn=conn)
        # print(result)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No data found"
            )
        # return {"databases": [db["Database"] for db in result]}
        return result



@app.get("/usersadd")
async def get_databases(conn: aiomysql.Connection = Depends(get_db),username: str = None,age: int =None ):
    async with db_transaction(conn):
        try:
            result = await execute_sql("INSERT INTO userxxx VALUES ('%s',%d)" % (username,age), conn=conn)
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
                # detail=e
            )


# --- 运行命令 ---
# if __name__ == "__main__":
#     import uvicorn
#
#     uvicorn.run(
#         app,
#         host="0.0.0.0",
#         port=8000,
#         reload=True,  # 启用热重载
#         server_header=False  # 安全增强
#     )

# --- 运行命令 ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
