# src/api/endpoints/chat.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import pickle
import os
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Optional
import logging
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

router = APIRouter()

# Загружаем модель для эмбеддингов
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
DATA_DIR = os.getenv('DATA_DIR', './data/processed')

# Путь к файлу с эмбеддингами
EMBEDDINGS_FILE = os.path.join(DATA_DIR, 'product_embeddings.pkl')
PRODUCTS_FILE = os.path.join(DATA_DIR, 'products_data.csv')

# Глобальные переменные для кэширования данных
embeddings_data = None
model = None

def load_data():
    """Загружает эмбеддинги и данные товаров."""
    global embeddings_data, model
    
    if embeddings_data is None:
        try:
            with open(EMBEDDINGS_FILE, 'rb') as f:
                embeddings_data = pickle.load(f)
            logger.info(f"Загружены эмбеддинги для {len(embeddings_data['product_ids'])} товаров")
        except FileNotFoundError:
            logger.error(f"Файл эмбеддингов не найден: {EMBEDDINGS_FILE}")
            raise HTTPException(status_code=500, detail="Данные эмбеддингов не найдены. Запустите скрипт загрузки данных.")
        except Exception as e:
            logger.error(f"Ошибка загрузки эмбеддингов: {e}")
            raise HTTPException(status_code=500, detail=f"Ошибка загрузки данных: {str(e)}")
    
    if model is None:
        try:
            model = SentenceTransformer(EMBEDDING_MODEL)
            logger.info(f"Модель {EMBEDDING_MODEL} загружена")
        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")
            raise HTTPException(status_code=500, detail=f"Ошибка загрузки модели: {str(e)}")
    
    return embeddings_data, model

# Модель для запроса
class ChatRequest(BaseModel):
    question: str
    limit: Optional[int] = 5  # Максимальное количество результатов

# Модель для ответа
class ProductResult(BaseModel):
    product_id: int
    name: str
    price: float
    description: str
    seo_url: str
    quantity: int
    similarity_score: float

class ChatResponse(BaseModel):
    query: str
    results: List[ProductResult]
    total_found: int

import re

@router.post("/chat", response_model=ChatResponse)
async def search_products(request: ChatRequest):
    """
    Продвинутый поиск купелей с фильтрацией диапазонов цен и сортировкой.
    Гарантированная совместимость типов для FastAPI/Pydantic.
    """
    logger.info(f"Запрос: '{request.question}'")
    
    # Загружаем данные
    data, model_instance = load_data()
    
    # Создаем эмбеддинг для вопроса. Модель возвращает двумерный массив (1, 384).
    # Делаем его одномерным вектором формы (384,) с помощью [0]
    question_embedding = model_instance.encode([request.question])[0]
    
    # Получаем эмбеддинги товаров
    product_embeddings = data['embeddings']  # Ожидается форма (N, 384)
    product_ids = data['product_ids']
    products_data = data['products_data']
    
    # БЕЗОПАСНОЕ КОСИНУСНОЕ СХОДСТВО
    # Нормализуем вектор вопроса
    norm_question = question_embedding / np.linalg.norm(question_embedding)
    
    # Нормализуем векторы продуктов
    product_norms = np.linalg.norm(product_embeddings, axis=1, keepdims=True)
    # Заменяем нули на единицы, чтобы избежать деления на 0
    product_norms[product_norms == 0] = 1.0
    norm_products = product_embeddings / product_norms
    
    # Вычисляем сходство. Результат — одномерный массив формы (N,)
    similarities = np.dot(norm_products, norm_question)
    
    # Получаем индексы, отсортированные по убыванию сходства
    top_indices = np.argsort(similarities)[::-1]
    
    query_lower = request.question.lower()
    
    # --- БЛОК УМНОЙ ФИЛЬТРАЦИИ ЦЕН ---
    max_price_limit = None
    min_price_limit = None
    
    def parse_numeric_value(text_num):
        text_num = text_num.replace(" ", "").replace(",", ".")
        if "к" in text_num or "k" in text_num:
            text_num = text_num.replace("к", "").replace("k", "")
            return float(text_num) * 1000
        if "тыс" in text_num:
            text_num = text_num.replace("тыс", "")
            return float(text_num) * 1000
        return float(text_num)

    # Ищем "до 300 000"
    max_price_match = re.search(r'(?:до|меньше|дешевле|бюджетнее)\s*(\d+(?:[\s,.]?\d*)*(?:\s*(?:к|k|тыс))?)', query_lower)
    if max_price_match:
        try:
            max_price_limit = parse_numeric_value(max_price_match.group(1))
            logger.info(f"Обнаружен фильтр: цена ДО {max_price_limit} руб.")
        except Exception:
            pass

    # Ищем "от 100 000"
    min_price_match = re.search(r'(?:от|дороже|больше|выше)\s*(\d+(?:[\s,.]?\d*)*(?:\s*(?:к|k|тыс))?)', query_lower)
    if min_price_match:
        try:
            min_price_limit = parse_numeric_value(min_price_match.group(1))
            logger.info(f"Обнаружен фильтр: цена ОТ {min_price_limit} руб.")
        except Exception:
            pass
    # --------------------------------------

    candidates = []
    for idx in top_indices:
        idx = int(idx)  # Приводим к чистому int
        product_id = int(product_ids[idx])
        
        # КРИТИЧЕСКИЙ ШАГ: Используем .item() для конвертации numpy.float32 в чистый Python float
        similarity = float(similarities[idx].item())
        
        # Порог схожести
        if similarity < 0.15:
            continue
            
        product_data = next((p for p in products_data if p['product_id'] == product_id), None)
        if product_data:
            price = float(product_data.get('price', 0))
            
            # Фильтрация по диапазонам цен
            if max_price_limit is not None and price > max_price_limit:
                continue
            if min_price_limit is not None and price < min_price_limit:
                continue
                
            candidates.append(ProductResult(
                product_id=product_id,
                name=str(product_data.get('name', 'Без названия')),
                price=price,
                description=str(product_data.get('description', ''))[:200],
                seo_url=str(product_data.get('seo_url', ''))[:250],
                quantity=int(product_data.get('quantity', 0)),
                similarity_score=similarity  # Теперь это точно чистый float
            ))

    # --- БЛОК СОРТИРОВКИ ---
    is_sorting_requested = any(w in query_lower for w in ["отсортируй", "сортировк", "по цене", "сначала", "упорядоч"])
    sort_descending = any(w in query_lower for w in ["дорог", "убыван", "больш", "высок"])
    sort_ascending = any(w in query_lower for w in ["дешев", "возрастан", "меньш", "низк"])
    
    if is_sorting_requested or sort_descending or sort_ascending:
        logger.info("Применяется сортировка по цене")
        reverse_order = True if sort_descending else False
        candidates.sort(key=lambda x: x.price, reverse=reverse_order)
    elif max_price_limit is not None or min_price_limit is not None:
        # Автоматическая сортировка от дешевых к дорогим при фильтрации по цене
        candidates.sort(key=lambda x: x.price)

    # Отрезаем результат до лимита
    results = candidates[:request.limit]
    logger.info(f"Возвращено {len(results)} результатов")
    
    return ChatResponse(
        query=request.question,
        results=results,
        total_found=len(results)
    )



@router.get("/health")
async def health_check():
    """Проверка работоспособности API."""
    return {"status": "ok", "message": "API для поиска купелей работает"}