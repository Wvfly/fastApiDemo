import logging
from logging.handlers import RotatingFileHandler
# from fastapi_cache.decorator import cache
from fastapi import FastAPI,Form,File,UploadFile,Request,HTTPException,WebSocket, WebSocketDisconnect,status
from pydantic import BaseModel
# from starlette import status
from starlette.responses import Response,JSONResponse
import os,httpx,asyncio,aioredis,json,psutil
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.staticfiles import StaticFiles
# from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from mysqlconnpool import execute_query
from cachetools import TTLCache     #适用于简单的内存缓存，适合开发或小型应用
#######################################################################
from aiocache import caches,cached,Cache,RedisCache     #使用异步缓存
from aiocache.serializers import JsonSerializer
from dbpool import AsyncMySQLPool
from contextlib import asynccontextmanager


# 设置日志级别和格式
os.makedirs('logs', exist_ok=True)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)     #可省略，因handler已继承basicConfig的级别

# 创建文件处理器并设置日志格式和文件名
file_handler = RotatingFileHandler("logs/main.out", maxBytes=100 * 1024 * 1024, backupCount=5, encoding="utf-8")  # 1MB, 5 backups
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)

# 将处理器添加到日志记录器中
logger.addHandler(file_handler)



class MyMiddleware(BaseHTTPMiddleware):
    '''
    通过中间件修改全局的响应头
    如果想要修改server字段，需要修改uvicon的config.py文件
    '''
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # 添加自定义响应头
        response.headers["version"] = "1.3.1"
        response.headers["Access-Control-Allow-Origin"] = "*"       #允许跨域
        return response

class Item(BaseModel):
    '''
    构造body请求体
    '''
    name: str
    description: str = None
    price: float
    tax: float = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化连接池，路由下面就不再需要初始化pool
    await pool.initialize()
    yield
    # 关闭时清理连接池
    await pool.close()


cache = TTLCache(maxsize=100, ttl=5)  # 启用缓存最多100条，存活5秒
pool = AsyncMySQLPool()

#初始化redis连接，如果不指定encoding编码，后续通过订阅getmessage信息为byte类型
redis_client = aioredis.from_url("redis://localhost:6379", encoding="utf-8", max_connections=100, decode_responses=True)

app = FastAPI(docs_url=None,redoc_url=None,openapi_url=None,lifespan=lifespan)
app.add_middleware(MyMiddleware)        #添加自定义中间件
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

def get_memory_usage():
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024  # 返回 MB 单位

templates = Jinja2Templates(directory="static")      #设置静态文件目录
# app.mount("/", StaticFiles(directory="static"), name="statics")      #全局静态文件路由，会覆盖templates，如果两者共存，可以放到最后指定


@app.get("/")       #全局静态路由根默认页
async def root(request:Request):
    return templates.TemplateResponse("index.html", {
        "request": request,  # 必须项
        "name": "index"
    })

@app.get("/hello/{name}")
# @cache(expire=60)
async def say_hello(name: str):
    return {"message": f"Hello {name}"}

#传参p
@app.get("/params")
async def params(p:str):
    return {"msg":p}

#body接收json类
@app.post("/items/{item_id}")
async def create_item(item_id: int, item: Item, q: str = None):
    print(dict(item).keys())
    result = {"item_id": item_id, **item.dict()}
    if q:
        result.update({"q": q})
    return result

#body接收表单类
@app.post("/form")
async def create_item(name: str = Form(...), description: str = Form(None), price: float = Form(...), tax: float = Form(None)):
    if not description:
        description="null"      #缺省表单
    item = Item(name=name, description=description, price=price, tax=tax)
    return item

#手动返回403
@app.get("/restricted")
async def read_restricted_item():
    return Response("操作不被允许",media_type='text/html',status_code=403)        ##Response默认返回json类型
    # return JSONResponse(status_code=403, content={"detail": "操作不被允许"})
    # return {"msg": "你有权限访问这个资源"}


#文件下载
@app.get("/download")
async def download():
    path = "upload/StarRocks-2.5.22.tar.gz"
    filename = "StarRocks-2.5.22.tar.gz"
    # with open(path + "/" + filename,'rb') as f:
        # response=Response(content=f.read(),media_type="text/plain;charset=utf-8")       #一次加载会有爆内存风险
        # response.headers['Content-Disposition'] = 'attachment; filename=%s' % filename
        #
        # return response

    try:
        return FileResponse(
            path=path,
            filename=filename
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="文件不存在")

#文件上传(纯接口)
@app.post("/uploadapi")
async def upload(file: UploadFile=File(...)):
    dir="upload"
    os.makedirs(dir,exist_ok=True)

    filename=file.filename
    # content=await file.read()     #一次加载会有爆内存风险
    filestorepath=os.path.join(dir,filename)

    with open(filestorepath,'wb') as f:
        # f.write(content)
        # while chunk := await file.read(1024 * 1024):  # 每次读取 1MB  (:= 海象运算符，python3.8+才支持)
        while True:
            chunk = await file.read(1024 * 1024)  # 每次读取 1MB
            if not chunk:  # 读到文件末尾时，chunk 为空字节
                break
            f.write(chunk)

    return {"msg":"upload successfully !","filename":filename}

#文件上传模板(web)
@app.post("/upload")
async def upload(request:Request,file: UploadFile=File(...)):
    dir="upload"
    os.makedirs(dir,exist_ok=True)

    filename=file.filename
    # content=await file.read()     #一次加载会有爆内存风险

    try:
        filestorepath=os.path.join(dir,filename)
        with open(filestorepath,'wb') as f:
            # f.write(content)
            while True:
                chunk = await file.read(1024 * 1024)  # 每次读取 1MB
                if not chunk:  # 读到文件末尾时，chunk 为空字节
                    break
                logger.debug(f"Current memory usage: {get_memory_usage():.2f} MB")
                f.write(chunk)
        message = "File uploaded successfully !"
        message_type = "success"

    except Exception as e:
        message = 'An unexpected error occurred' + str(e)
        message_type = "error"

    return templates.TemplateResponse("templates/index.html", {
        "request": request,
        'message': message,
        'message_type': message_type
        }
    )

#渲染html，这里用了文件上传作为demo
@app.get("/upload")
async def static(request:Request):
    return templates.TemplateResponse("templates/upload.html", {
        "request": request,     #必须项
        "name": "upload"
        }
    )

#反向代理
@app.api_route("/proxy/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def reverse_proxy(path: str, request: Request):
    target_url = f"http://bigdata-online-3:8088/{path}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                request.method,
                target_url,
                content=await request.body(),
                headers=dict(request.headers)
            )
            return Response(content=response.content, status_code=response.status_code)
        except httpx.RequestError:
            raise HTTPException(status_code=500, detail="Proxy request failed")

#反向代理
@app.api_route("/static/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def reverse_proxy(path: str, request: Request):
    target_url = f"http://bigdata-online-3:8088/static/{path}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                request.method,
                target_url,
                content=await request.body(),
                headers=dict(request.headers)
            )
            return Response(content=response.content, status_code=response.status_code)
        except httpx.RequestError:
            raise HTTPException(status_code=500, detail="Proxy request failed")

#简单的websocket用例
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()  # 接受客户端连接
    try:
        while True:
            data = await websocket.receive_text()  # 接收文本消息
            await websocket.send_text(f"服务器响应: {data}")  # 发送消息
    except WebSocketDisconnect:
        logger.info("客户端断开连接")  # 捕获断开异常‌


#使用 Redis 发布/订阅机制实现跨进程通信：所有进程订阅同一频道，任一进程收到消息后广播到所有连接的客户端‌
# 进程启动时订阅消息
async def subscribe_messages(websocket: WebSocket):
    # pubsub = redis_client.pubsub()
    # await pubsub.subscribe("broadcast_channel")
    # try:
    #     while True:
    #         message = await pubsub.get_message(ignore_subscribe_messages=True)
    #         ##消息的数据结构{'type': 'message', 'pattern': None, 'channel': 'xxx', 'data': 'xxxxxx'}
    #         if message:
    #             msg = message["data"]
    #             logger.info(message)
    #             await websocket.send_text(msg)
    # except Exception as e:
    #     logger.exception(e)
    #     pubsub.unsubscribe("broadcast_channel")
    #     pubsub.close()

    pubsub = redis_client.pubsub()
    await pubsub.subscribe("broadcast_channel")
    try:
        async for message in pubsub.listen():  # 使用listen方法异步迭代监听,get_message()是非阻塞轮询，空循环会消耗大量CPU
            if message["type"] == "message":
                ##消息的数据结构{'type': 'message', 'pattern': None, 'channel': 'xxx', 'data': 'xxxxxx'}
                msg = message["data"]
                logger.info(f"Broadcasting message: {msg}")
                await websocket.send_text(msg)
    except Exception as e:
        logger.error(f"订阅错误: {e}", exc_info=True)
    finally:
        await pubsub.unsubscribe("broadcast_channel")
        await pubsub.close()

# HTTP 接口触发消息广播
@app.post("/broadcast")
async def broadcast_message(message: str = Form(...)):
    await redis_client.publish("broadcast_channel", message)
    return {"messages sended": "OK"}



@app.websocket("/ws1")
async def ws1(websocket:WebSocket):
    await websocket.accept()
    task = asyncio.create_task(subscribe_messages(websocket))
    try:
        while True:
            # 维持连接并检测断开
            await websocket.receive_text()
    except WebSocketDisconnect:
        # 客户端断开时取消任务
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    # finally:
    #     await websocket.close()       #不需要显式关闭



#非异步mysql，异步mysql样例详见useradd.py,或asyncmysqldemo.py（这个还没看明白）
@app.get("/usersadd")
async def useradd(username: str = None,age: int =None):
    try:
        result = execute_query("INSERT INTO userxxx VALUES ('%s',%d)" % (username,age))
        logger.debug("sql执行：%s" % result)
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

#使用内存缓存的简单案例
@app.get("/getdb")
async def getdb():
    if "db" in cache:
        return cache["db"]
    else:
        try:
            result = execute_query("select sleep(3)")
            logger.debug("sql执行：%s" % result)
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No data found"
                )
            cache["db"]=result
            return result
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=e
            )


##使用异步内存缓存,先路由，再缓存
@app.get("/getdb1")
@cached(cache=Cache.MEMORY, serializer=JsonSerializer(), ttl=5)     #缓存5秒
async def getdb1():
    try:
        result = execute_query("select sleep(3)")
        logger.debug("sql执行：%s" % result)
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

# ##使用异步redis缓存,先路由，再缓存
rediscache = Cache(
    Cache.REDIS,
    endpoint="localhost",  # Redis服务器地址
    port=6379,             # 端口
    db=0,                  # 数据库编号
    # password="your_password", # 认证密码（可选）
    serializer=JsonSerializer(), # 序列化器
    pool_max_size=20       # 连接池大小
)
@app.get("/getdb2")
@cached(
    cache=Cache.REDIS,
    key="db",
    ttl=60,  # 缓存5秒
    serializer=JsonSerializer()
)
async def getdb2():
    try:
        # 模拟异步数据库查询（需真实替换为你的查询逻辑）
        # result = await execute_query("SELECT SLEEP(3)")
        result = await pool.fetch_all("SELECT SLEEP(3)")        #需要异步的操作
        logger.debug(f"SQL执行结果: {result}")

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No data found"
            )
        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)  # 必须转为字符串！
        )


app.mount("/", StaticFiles(directory="static"), name="statics")      #全局静态文件路由
if __name__ == '__main__':
    import uvicorn
    # uvicorn.run(app, host='0.0.0.0', port=8000)
    # uvicorn.run(app, host='::', port=8000)

    conf = 'config/fastlog.conf'
    with open(conf) as f:
        logconf = f.read()
        logconf = json.loads(logconf)
        # print(logconf)

    uvicorn.run(app, host="127.0.0.1", port=8000, log_config=logconf)




