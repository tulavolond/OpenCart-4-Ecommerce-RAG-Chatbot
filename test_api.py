# test_api.py
import requests
import json

url = "http://localhost:8000/api/v1/chat"
data = {
    "question": "Купель с печью от 200 000 до 500 000",
    "limit": 5
}

response = requests.post(url, json=data)
print(json.dumps(response.json(), indent=2, ensure_ascii=False))