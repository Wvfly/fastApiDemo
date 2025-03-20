from fastapi import FastAPI
import logging
from logging.handlers import RotatingFileHandler

# 设置日志级别和格式
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 创建文件处理器并设置日志格式和文件名
file_handler = RotatingFileHandler('fastapi.log', maxBytes=100 * 1024 * 1024, backupCount=5)  # 1MB, 5 backups
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# 将处理器添加到日志记录器中
logger.addHandler(file_handler)

app = FastAPI(docs_url=None,redoc_url=None,openapi_url=None)


@app.get("/")
async def root():
    logger.info("root access")
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


if __name__ == '__main__':
    import uvicorn,json

    conf='fastlog.conf'
    with open(conf) as f:
        logconf=f.read()
        logconf=json.loads(logconf)
        print(logconf)

    uvicorn.run(app,host="0.0.0.0",port=8000,log_config=logconf)
