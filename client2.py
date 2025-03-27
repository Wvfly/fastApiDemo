import asyncio
from dbpool import AsyncMySQLPool

pool = AsyncMySQLPool()

async def sql1():
    result = await pool.fetch_all("SELECT NOW() AS current_times")
    print("SQL1 result:", result)


async def sql2():
    result = await pool.fetch_all("SELECT SLEEP(3)")
    print("SQL2 result:", result)

async def sql3():
    result = await pool.fetch_all("SELECT * from userxxx")
    print("SQL3 result:", result)


async def main():
    await pool.initialize()
    try:
        while True:
            print("Pool initialized:", pool.pool_status())

            tasks = [
                # 可以使用asyncio.create_task创建任务，也可以直接添加函数名，因为asyncio.wait内部逻辑会自动为每个协程执行ensure_future从而封装为Task对象
                asyncio.create_task(sql1(), name="sql1"),
                asyncio.create_task(sql2(), name="sql2"),
                asyncio.create_task(sql3(), name="sql3")
                # sql1(),
                # sql2(),
                # sql3()
            ]
            done, pending = await asyncio.wait(tasks, timeout=None)

            for task in done:
                if task.exception():
                    print(f"Task {task.get_name()} failed:", task.exception())
    except Exception as e:
        print(e)
        await pool.close()



if __name__ == "__main__":
    asyncio.run(main())