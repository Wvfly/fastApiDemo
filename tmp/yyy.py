import time
import asyncio

def yyy():
    a = 0
    while True:
        a = yield a
        if a is not None:
            a += 1

def xxx():
    yield 1
    yield 2
    yield 3

f=yyy()
next(f)
print(f.send(10))
print(f.send(11))
#
# x=xxx()
# for i in range(5):
#     print(next(x))

def x_from():
        while True:
            yield from xxx()

b=x_from()
for i in range(5):
    print(next(b))

print('=====================')

def func1():
    yield 1
    yield from func2()
    yield 2


def func2():
    yield 3
    yield 4


f1 = func1()
for item in f1:
    print(item)

print("=========================================")




@asyncio.coroutine
def func1():
    print(1)
    yield from asyncio.sleep(2.1)  # 遇到IO耗时操作，自动化切换到tasks中的其他任务
    print(2)


@asyncio.coroutine
def func2():
    print(3)
    yield from asyncio.sleep(2)  # 遇到IO耗时操作，自动化切换到tasks中的其他任务
    print(4)


tasks = [
    asyncio.ensure_future(func1()),
    asyncio.ensure_future(func2())
]

loop = asyncio.get_event_loop()
loop.run_until_complete(asyncio.wait(tasks))


print('==================通过事件循环==================')

def stop(times):
    time.sleep(times)

async def ccc1():
    print('协程逻辑1')
    await asyncio.sleep(2)
    print('结束协程逻辑1')

async def ccc2():
    print('协程逻辑2')
    await asyncio.sleep(0.8)
    print('结束协程逻辑2')

# asyncio.run(ccc1())
# asyncio.run(ccc2())

loop=asyncio.get_event_loop()
# 将协程添加到事件循环#然后事件循环检测task2中的任务是否就绪，就绪则执行代码
task2=[
    asyncio.ensure_future(ccc1()),
    asyncio.ensure_future(ccc2())
]
# 然后事件循环检测task2中的任务是否就绪，就绪则执行代码
loop.run_until_complete(asyncio.wait(task2))

# 把协程封装成task对象
print('==================把协程封装成task对象==================')

async  def main():
    task3=[
        asyncio.create_task(ccc1()),
        asyncio.create_task(ccc2())
    ]

    # asyncio.wait
    # 源码内部会对列表中的每个协程执行ensure_future从而封装为Task对象，所以在和wait配合使用时task_list的值为[
    #     func(), func()]
    # 也是可以的
    # task4=[
    #     ccc1(),
    #     ccc2()
    # ]

    done,pendding = await asyncio.wait(task3,timeout=None)
    print(done,pendding)

asyncio.run(main())



## 另外的写法
# task4 = [
#     ccc1(),
#     ccc2()
# ]
# asyncio.run(asyncio.wait(task4))