import pandas as pd
from datetime import datetime, date
import os

try:
    print("Початок створення файлу...")

    # Створюємо тестові дані
    data = {
        'month': [
            '2024-03-01', '2024-03-01',  # Березень 2024
            '2024-04-01', '2024-04-01'   # Квітень 2024
        ],
        'category': [
            'видача', 'збір',  # Категорії для березня
            'видача', 'збір'   # Категорії для квітня
        ],
        'sum': [
            50000, 45000,  # Суми для березня
            55000, 48000   # Суми для квітня
        ]
    }

    # Створюємо DataFrame
    df = pd.DataFrame(data)
    print("\nDataFrame створено:")
    print(df)

    # Конвертуємо дати в правильний формат
    df['month'] = pd.to_datetime(df['month']).dt.date
    print("\nДати конвертовано")

    # Шлях до робочого столу
    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    print(f"\nШлях до робочого столу: {desktop_path}")

    # Повний шлях до файлу
    file_path = os.path.join(desktop_path, 'test_plans.xlsx')
    print(f"Повний шлях до файлу: {file_path}")

    # Зберігаємо в Excel
    df.to_excel(file_path, index=False)

    print(f"\nФайл створено успішно: {file_path}")
    print("Перевірте файл на робочому столі")

except Exception as e:
    print(f"\nПомилка при створенні файлу:")
    print(f"Тип помилки: {type(e).__name__}")
    print(f"Опис помилки: {str(e)}")
    print(f"Поточна директорія: {os.getcwd()}")
