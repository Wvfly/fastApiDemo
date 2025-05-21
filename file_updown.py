from applog import LogClass
from fastapi import FastAPI,File,UploadFile,Request #,Query
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException
from fastapi.responses import FileResponse,HTMLResponse
import os,json,re

genlog=LogClass()
genlog.initialize()
logger=genlog.logger

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


app = FastAPI(
    # lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    # redirect_slashes=False             #禁用自动重定向机制‌，FastAPI 会直接匹配已注册的路由，而非尝试修正路径斜杠‌，设置似乎没什么卵用
)
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
# 文件上传下载目录
UPLOAD_DIR = "upload"
os.makedirs(UPLOAD_DIR, exist_ok=True)
# 文件列表接口
@app.get("/api/files")
async def get_file_list():
    files = []
    for filename in os.listdir(UPLOAD_DIR):
        file_path = os.path.join(UPLOAD_DIR, filename)
        stat = os.stat(file_path)
        files.append({
            "name": filename,
            "size": stat.st_size,
            "mtime": stat.st_mtime
        })
    logger.debug(files)
    return files

# 文件下载路由
@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream'
    )

# 下载页面路由
@app.get("/download", response_class=HTMLResponse)
async def download_page(request: Request):
    return templates.TemplateResponse("templates/download.html", {"request": request})


#文件上传模板(web)
@app.post("/upload")
async def upload(request:Request,file: UploadFile=File(...)):
    # dir="upload"
    # os.makedirs(U,exist_ok=True)

    filename=file.filename
    # content=await file.read()     #一次加载会有爆内存风险

    try:
        filestorepath=os.path.join(UPLOAD_DIR,filename)
        with open(filestorepath,'wb') as f:
            # f.write(content)
            while True:
                chunk = await file.read(1024 * 1024)  # 每次读取 1MB
                if not chunk:  # 读到文件末尾时，chunk 为空字节
                    break
                # logger.debug(f"Current memory usage: {get_memory_usage():.2f} MB")
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

#渲染html，这里用了文件上传作为demo，通过双路由使得uri尾部有无斜杠都能被解析到
@app.get("/upload")
@app.get("/upload/")
async def static(request:Request):
    return templates.TemplateResponse("templates/upload.html", {
        "request": request,     #必须项
        "name": "upload"
        }
    )

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

@app.get("/")       #全局静态路由根默认页
async def root(request:Request):
    return templates.TemplateResponse("index.html", {
        "request": request,  # 必须项
        "name": "index"
    })


app.mount("/", StaticFiles(directory="static"), name="statics")      #全局静态文件路由
if __name__ == '__main__':
    import uvicorn,sys
    try:
        host=sys.argv[1]
        port=int(sys.argv[2])
    except:
        logger.warning("Do not specify the bindding ip and port,then useed 127.0.0.1:8000 instead !")
        host="127.0.0.1"
        port=8000
    conf = "config/fastlog.conf"
    with open(conf) as f:
        logconf = f.read()
        logconf = json.loads(logconf)
        # print(logconf)

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_config=logconf,
        ssl_certfile="config/ssl.crt",      #tls证书
        ssl_keyfile="config/ssl.key"        #tls私钥
    )