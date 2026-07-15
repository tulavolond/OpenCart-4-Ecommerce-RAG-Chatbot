# test_preprocess.py
import pandas as pd
import os

def test_preprocessing():
    """Проверка результатов предобработки"""
    
    # Проверяем, существуют ли файлы
    processed_files = [
        'data/processed/processed_products.csv',
        'data/processed/processed_orders.csv'
    ]
    
    for file_path in processed_files:
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            print(f"✓ {file_path} создан")
            print(f"  - Строк: {len(df)}")
            print(f"  - Столбцов: {len(df.columns)}")
            print(f"  - Первые 2 строки:\n{df.head(2)}\n")
        else:
            print(f"✗ {file_path} не найден")

if __name__ == "__main__":
    test_preprocessing()