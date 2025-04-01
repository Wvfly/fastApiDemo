### fastapi 用例
编译打包： nuitka --onefile --standalone --disable-ccache main.py

依赖：pip install fastapi uvicorn aioredis httpx pydantic jinja2 python-multipart nuitka psutil websockets aiocache[redis] cachetools aiomysql
