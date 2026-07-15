# src/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from .endpoints import chat  # Импортируем новый модуль

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="API для поиска купелей",
    description="Семантический поиск купелей с помощью RAG",
    version="1.0.0"
)

# Настройка CORS для доступа с сайта
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене заменить на ваш домен
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем эндпоинты
app.include_router(chat.router, prefix="/api/v1", tags=["Поиск купелей"])

@app.get("/")
async def root():
    return {
        "message": "Добро пожаловать в API для поиска купелей!",
        "docs": "/docs",
        "health": "/api/v1/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)