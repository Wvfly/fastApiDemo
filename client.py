import requests
import json

body = {
      "name": "yanshu",
      "description": "yanshu's blog",
      "price": 100,
      "tax": 0
    }

body = json.dumps(body) # 需要先解析
print(body)

response = requests.put('http://127.0.0.1:8888/items/3?q=qweqwe',data = body)
print(response.text)