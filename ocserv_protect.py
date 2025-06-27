from applog import LogClass
from fastapi import FastAPI,Request,Response,Depends
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.templating import Jinja2Templates
from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException
import os,json,re,time
from monitor import REQUEST_LATENCY, monitor_request
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import datetime,threading

genlog=LogClass()
genlog.initialize()
logger=genlog.logger
sessions = {}   # Session存储(实际项目中建议使用Redis等)
cleanup_interval = 120  # 定时清理一次token

# 500页面指定返回头
security_headers = {
    # "Strict-Transport-Security": "max-age=63072000",
    "X-Powered-By": "PHP/5.6.40",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY"
}

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
        response.headers["X-Frame-Options"] = "DENY"
        return response

# 安全中间件
security = HTTPBearer()

# def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
#     token = credentials.credentials
#     if token not in sessions:
#         raise HTTPException(status_code=401, detail="Invalid session token")
#     return token

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    session_data = sessions.get(token)

    if not session_data:
        raise HTTPException(401, "Invalid session token")

    if datetime.datetime.now() > session_data["expire_time"]:
        del sessions[token]  # 清理过期session
        raise HTTPException(401, "Session expired")

    return token

# 清理过期token
def cleanup_expired_tokens():
    """定时清理过期token的后台线程"""
    while True:
        now = datetime.datetime.now()
        expired_tokens = [
            token for token, data in sessions.items()
            if now > data["expire_time"]
        ]
        for token in expired_tokens:
            del sessions[token]
        time.sleep(cleanup_interval)

# 启动清理线程
cleaner_thread = threading.Thread(
    target=cleanup_expired_tokens,
    daemon=True
)
cleaner_thread.start()

app = FastAPI(
    # lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    # redirect_slashes=False             #禁用自动重定向机制‌，FastAPI 会直接匹配已注册的路由，而非尝试修正路径斜杠‌，设置似乎没什么卵用
)

# prometheus中间件
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    REQUEST_LATENCY.labels(
        method=request.method,
        path=request.url.path
    ).observe(process_time)

    monitor_request(request, response)
    return response

app.add_middleware(MyMiddleware)        #添加自定义中间件
templates = Jinja2Templates(directory="static")      #设置静态文件目录

# 修改默认的错误返回页面，防止泄露框架特征
@app.exception_handler(404)
async def handler_page404_(request, exc):
    # return FileResponse(
    #     "templates/404.html",     # FileResponse方法加载的是项目的物理路径
    #     status_code=404,
    #     media_type="text/html"
    # )
    return templates.TemplateResponse(
        "templates/404.html",       # TemplateResponse方法加载的是前面Jinja2设置的目录为根目录后的路径
        {
            "request": request,  # 必须项
            "name": "页面不存在"
        },
        status_code=404
    )

# 其他4xx页面
@app.exception_handler(HTTPException)
async def handler_4xx(request,exc):
    return JSONResponse(status_code=exc.status_code, content={"msg":"request error","code":exc.status_code})

# 500页面
@app.exception_handler(Exception)
async def handler_exception(request,exc):
    logger.error(f"500 Error: {str(exc)}", extra={"path": request.url.path})
    return templates.TemplateResponse(
        "templates/err.html",  # TemplateResponse方法加载的是前面Jinja2设置的目录为根目录后的路径
        {
            "request": request,  # 必须项
            "name": "程序异常"
        },
        headers=security_headers,
        status_code=500
    )



############################### 路由开始 ###############################
whitelist=[]

# prometheus监控
@app.get("/qitouxxx")
async def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

@app.get("/login.html")
async def static(request:Request):
    return templates.TemplateResponse("templates/login.html", {
        "request": request,     #必须项
        "name": "login"
        }
    )

@app.get("/whitelist.html")
async def static(request:Request):
    return templates.TemplateResponse("templates/whitelist.html", {
        "request": request,     #必须项
        "name": "whitelist"
        }
    )

# 查询白名单
@app.get("/whitelist")
async def white_list(token: str = Depends(verify_token)):
    result={"Host": whitelist}
    logger.debug(sessions)
    return result

# 登录接口
@app.post("/auth")
async def create_item(request: Request):
    body = await request.body()  # 解析JSON数据
    item=json.loads(body)
    if item["username"] == "****" and item["password"] == "****":
    # TODO 用户注册，用户校验
        RemoteHost=request.client.host
        session_token = os.urandom(16).hex()  # 生成随机token
        expire_time = datetime.datetime.now() + datetime.timedelta(seconds=120)  # 2分钟后过期
        if RemoteHost not in whitelist:
            # cmd = "iptables -I INPUT -s %s -p tcp --dport 443 -j ACCEPT" % RemoteHost
            cmd = "iptables -I INPUT -s %s -j ACCEPT;iptables -I DOCKER -s %s -j ACCEPT;" % (RemoteHost,RemoteHost)
            os.system(cmd)
            logger.info(cmd)
            whitelist.append(RemoteHost)
            logger.info(request.client)

            msg={
                "authority": "Succeed",
                "info": "Host %s has added to whitelist !",
                "token": session_token
            }
        else:
            msg={
                "authority": "Succeed",
                "info": "Host %s has aleady in whitelist !",
                "token": session_token
            }
        # 存储session
        sessions[session_token] = {
            "username": item["username"],
            "ip": RemoteHost,
            # "login_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            # "expire_time": expire_time.strftime("%Y-%m-%d %H:%M:%S")
            "login_time": datetime.datetime.now(),
            "expire_time": expire_time
        }
    else:
        logger.warning("login failed , %s" % body.decode(encoding="utf-8"))
        msg={
            "authority": "Failed",
            "info": "Username or Password was incorrect !"
        }
    return msg

# 模拟400页面
# @app.get("/page400")
# async def read_item(q: str = Query(min_length=3)):
#     return {"q": q}

# 模拟500页面
@app.get("/page500")
async def page500(request:Request):
    raise ValueError("err")

# 攻击请求返回403拒绝页面
@app.get("/{path}")
async def api(request:Request,path: str):
    if re.search(r"php|api|password|passwd|cgi|query|bash|sh|perl|curl|env|git|yaml|xml",path):
        return templates.TemplateResponse("templates/403.html", {
            "request": request,     #必须项
            "name": "permission deny"
            },
            status_code=403
        )
    else:
        raise HTTPException(404)

# @app.get("/")       #全局静态路由根默认页
# async def root(request:Request):
#     return templates.TemplateResponse("index.html", {
#         "request": request,  # 必须项
#         "name": "index"
#     })
# app.mount("/", StaticFiles(directory="static"), name="statics")      #全局静态文件路由
if __name__ == '__main__':
    import uvicorn,sys
    try:
        host=sys.argv[1]
        port=int(sys.argv[2])

    except:
        logger.warning("Do not specify the bindding ip and port or workers,then useed 127.0.0.1:8000 for lancher !")
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
        ssl_keyfile=tls_key,
    )