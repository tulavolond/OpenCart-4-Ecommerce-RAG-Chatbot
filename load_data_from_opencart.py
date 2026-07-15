# scripts/load_data_from_opencart.py
import mysql.connector
import pandas as pd
import pickle
import os
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Конфигурация базы данных OpenCart
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME'),
    'port': os.getenv('DB_PORT')
}


# Конфигурация модели для эмбеддингов
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
DATA_DIR = os.getenv('DATA_DIR', './data/processed')

def load_products_from_db():
    """Загружает товары из базы данных OpenCart."""
    logger.info("Подключение к базе данных OpenCart...")
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # SQL-запрос для получения товаров (только включенные и с описанием)
        query = """
            SELECT 
                p.product_id, 
                pd.name, 
                pd.description, 
                p.price, 
                p.quantity, 
                p.model, 
                p.image,
                sd.keyword AS seo_url
            FROM oc_product p 
            LEFT JOIN oc_product_description pd ON (p.product_id = pd.product_id AND pd.language_id = 1) 
            LEFT JOIN oc_seo_url sd ON (sd.value = p.product_id AND sd.key = 'product_id' AND sd.language_id = 1)
            WHERE p.status = 1 
                AND pd.name IS NOT NULL 
                AND pd.name != '' 
            ORDER BY p.product_id

        """
        
        cursor.execute(query)
        products = cursor.fetchall()
        cursor.close()
        conn.close()
        
        logger.info(f"Загружено {len(products)} товаров из базы данных")
        return products
        
    except mysql.connector.Error as e:
        logger.error(f"Ошибка при подключении к базе данных: {e}")
        return []

def create_product_text(product):
    """Создает текстовое представление товара для эмбеддинга."""
    # Собираем информацию из разных полей
    parts = [
        product.get('name', ''),
        product.get('description', ''),
        f"Модель: {product.get('model', '')}",
        f"Ссылка: {product.get('seo_url', '')}",
        f"Цена: {product.get('price', '')} руб."
    ]
    
    # Фильтруем пустые части и объединяем
    text = " ".join([part for part in parts if part and part != 'None'])
    return text

def create_embeddings(products):
    """Создает эмбеддинги для всех товаров."""
    logger.info(f"Создание эмбеддингов для {len(products)} товаров...")
    
    if not products:
        logger.warning("Нет товаров для создания эмбеддингов")
        return None
    
    model = SentenceTransformer(EMBEDDING_MODEL)
    
    # Создаем тексты для эмбеддингов
    texts = [create_product_text(product) for product in products]
    product_ids = [product['product_id'] for product in products]
    
    # Создаем эмбеддинги
    embeddings = model.encode(texts, show_progress_bar=True)
    
    # Сохраняем результаты
    data = {
        'product_ids': product_ids,
        'embeddings': embeddings,
        'products_data': products
    }
    
    return data

def save_embeddings(data):
    """Сохраняет эмбеддинги в файл."""
    if not data:
        logger.warning("Нет данных для сохранения")
        return
    
    os.makedirs(DATA_DIR, exist_ok=True)
    filepath = os.path.join(DATA_DIR, 'product_embeddings.pkl')
    
    with open(filepath, 'wb') as f:
        pickle.dump(data, f)
    
    logger.info(f"Эмбеддинги сохранены в {filepath}")
    
    # Сохраняем также список товаров для быстрого доступа
    products_df = pd.DataFrame(data['products_data'])
    products_file = os.path.join(DATA_DIR, 'products_data.csv')
    products_df.to_csv(products_file, index=False)
    logger.info(f"Данные товаров сохранены в {products_file}")

def main():
    """Основная функция."""
    logger.info("Начало загрузки данных из OpenCart...")
    
    # 1. Загружаем товары из базы данных
    products = load_products_from_db()
    if not products:
        logger.error("Не удалось загрузить товары. Проверьте подключение к базе данных.")
        return
    
    # 2. Создаем эмбеддинги
    embeddings_data = create_embeddings(products)
    if embeddings_data is None:
        logger.error("Не удалось создать эмбеддинги")
        return
    
    # 3. Сохраняем результаты
    save_embeddings(embeddings_data)
    
    logger.info("Загрузка данных успешно завершена!")

if __name__ == "__main__":
    main()