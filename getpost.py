from applog import LogClass
from fastapi import FastAPI,Request
from starlette.responses import JSONResponse
import json,os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

'''
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
'''
genlog=LogClass()
genlog.initialize()
logger=genlog.logger

class MyMiddleware(BaseHTTPMiddleware):
    '''
    通过中间件修改全局的响应头
    如果想要修改server字段，需要修改uvicon的config.py文件，或者在启动时候指定头部信息uvicorn.run(...,headers=[("server","cat")])
    '''
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # 添加自定义响应头
        # response.headers["version"] = "1.3.1"
        response.headers["X-Powered-By"] = "PHP/5.6.40"               #伪装成php,戏耍攻击者
        # response.headers["Access-Control-Allow-Origin"] = "*"       #允许跨域
        response.headers["x-content-type-options"] = "nosniff"        #防止XSS攻击
        return response

app = FastAPI(
    # lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    # redirect_slashes=False             #禁用自动重定向机制‌，FastAPI 会直接匹配已注册的路由，而非尝试修正路径斜杠‌，设置似乎没什么卵用
)
app.add_middleware(MyMiddleware)        #添加自定义中间件

@app.exception_handler(StarletteHTTPException)
async def custom_except_handler(request, exc):
    #return Response('{"msg":"request error","code":%d}' % exc.status_code, media_type='application/json', status_code=exc.status_code)
    return JSONResponse(status_code=exc.status_code, content={"msg":"request error","code":exc.status_code})

@app.post("/")
async def create_item(request: Request):
    item = await request.body()  # 解析JSON数据
    # return item
    logger.info(item)
    logger.info(request.headers)
    return {"info":"ok"}



if __name__ == '__main__':
    import uvicorn,sys
    try:
        host=sys.argv[1]
        port=int(sys.argv[2])
    except:
        logger.warning("Do not specify the bindding ip and port or workers,then useed 127.0.0.1:8000  for lancher !")
        host="127.0.0.1"
        port=8000
    conf = "config/fastlog.conf"
    with open(conf) as f:
        logconf = f.read()
        logconf = json.loads(logconf)
        # print(logconf)

    tls_cert="config/ssl.crt"       #tls证书
    tls_key="config/ssl.key"        #tls私钥
    if not os.path.exists(tls_cert):
        tls_cert=None
        tls_key=None

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_config=logconf,
        ssl_certfile=tls_cert,
        ssl_keyfile=tls_key
    )



