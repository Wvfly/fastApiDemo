import requests,json,asyncio,time
from dbpool import AsyncMySQLPool

# body = {
#       "name": "yanshu",
#       "description": "yanshu's blog",
#       "price": 100,
#       "tax": 0
#     }
#
# body = json.dumps(body) # 需要先解析
# print(body)
#
# response = requests.put('http://127.0.0.1:8888/items/3?q=qweqwe',data = body)
# print(response.text)


pool = AsyncMySQLPool()
async def main():
    semaphore = asyncio.Semaphore(2)  # 限制并发数
    await pool.initialize()  # 连接池初始化

    # 包装任务函数以集成信号量控制
    async def controlled_task(query):
        async with semaphore:
            return await pool.fetch_all(query)

        # if await semaphore.acquire():
        #     try:
        #         msg = await pool.fetch_all(query)
        #         semaphore.release()
        #         return msg
        #     except Exception as e:
        #         semaphore.release()
        #         return e

    # 串行任务
    pre=await pool.fetch_all("show databases")
    print(pre)
    await asyncio.sleep(10)
    print("============================================================")

    end=await pool.fetch_all("select 100")
    print(end)
    print("============================================================")


    # 创建受控任务列表(并发执行)
    tasks = [
        controlled_task("SELECT SLEEP(5)"),
        controlled_task("SELECT SLEEP(10)"),
        controlled_task("SELECT UNIX_TIMESTAMP()"),
        controlled_task("SELECT SLEEP(3)"),
        controlled_task("SELECT UNIX_TIMESTAMP()"),
        controlled_task("insert into userxxx values ('ccccc',333)")
    ]

    # 并发执行所有任务（实际受信号量控制为串行）
    results = await asyncio.gather(*tasks)
    print(results)

    await pool.close()  # 正确关闭连接池
    return results



if __name__ == "__main__":
    print(time.asctime())
    asyncio.run(main())
    print(time.asctime())