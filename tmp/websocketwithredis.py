from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import aioredis
import asyncio

app = FastAPI(docs_url=None,redoc_url=None,openapi_url=None)

# Redis 连接池初始化
@app.on_event("startup")
async def startup():
    app.redis = await aioredis.from_url("redis://localhost:6379", encoding="utf-8", decode_responses=True)

@app.on_event("shutdown")
async def shutdown():
    await app.redis.close()

# 订阅任务,订阅频道，将频道新消息通过websoket发送出去
async def subscribe_task(websocket: WebSocket, channel: str):
    pubsub = app.redis.pubsub()
    await pubsub.subscribe(channel)
    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True)
            #消息的数据结构{'type': 'message', 'pattern': None, 'channel': 'xxx', 'data': 'xxxxxx'}
            if msg:
                await websocket.send_text(f"频道 {channel}: {msg['data']}")
            await asyncio.sleep(0.01)
    except WebSocketDisconnect:
        await pubsub.unsubscribe(channel)
        await pubsub.close()

# WebSocket 路由
@app.websocket("/ws/{channel}")
async def websocket_channel(websocket: WebSocket, channel: str):
    await websocket.accept()
    task = asyncio.create_task(subscribe_task(websocket, channel))
    try:
        while True:
            data = await websocket.receive_text()
            await app.redis.publish(channel, f"用户说: {data}")
    except WebSocketDisconnect:
        task.cancel()
        # await websocket.close()       #不需要显式关闭

# 广播接口，通过调用广播，把消息推送给每个websocket的客户端
@app.post("/broadcast/{channel}")
async def broadcast(channel: str, message: str):
    await app.redis.publish(channel, message)
    return {"status": "OK"}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)