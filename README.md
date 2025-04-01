# Кредитний HTTP-сервіс

REST API сервіс для роботи з кредитною базою даних.

## Вимоги

- Python 3.9+
- FastAPI
- MySQL
- SQLAlchemy

## Встановлення

1. Клонуйте репозиторій:
```bash
git clone <repository-url>
cd <repository-name>
```

2. Створіть віртуальне середовище та активуйте його:
```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
venv\Scripts\activate     # для Windows
```

3. Встановіть залежності:
```bash
pip install -r requirements.txt
```

4. Створіть базу даних MySQL:
```sql
CREATE DATABASE dictionary;
```

5. Оновіть параметри підключення до бази даних у файлі `app/database.py`

6. Імпортуйте дані з CSV-файлів:
```sql
-- Створення таблиці users
CREATE TABLE users (
    id INT PRIMARY KEY,
    login VARCHAR(100) NOT NULL UNIQUE,
    registration_date DATE NOT NULL
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Імпорт даних з users.csv
LOAD DATA LOCAL INFILE 'path/to/users.csv'
INTO TABLE users
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(id, login, @registration_date)
SET registration_date = STR_TO_DATE(@registration_date, '%d.%m.%Y');

-- Створення таблиці dictionary
CREATE TABLE dictionary (
    id INT PRIMARY KEY,
    name VARCHAR(255) NOT NULL
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Імпорт даних з dictionary.csv
LOAD DATA LOCAL INFILE 'path/to/dictionary.csv'
INTO TABLE dictionary
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

-- Створення таблиці credits
CREATE TABLE credits (
    id INT PRIMARY KEY,
    user_id INT NOT NULL,
    issuance_date DATE NOT NULL,
    return_date DATE NOT NULL,
    actual_return_date DATE,
    body DECIMAL(10,2) NOT NULL,
    percent DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Створення таблиці payments
CREATE TABLE payments (
    id INT PRIMARY KEY,
    sum DECIMAL(10,2) NOT NULL,
    payment_date DATE NOT NULL,
    credit_id INT NOT NULL,
    type_id INT NOT NULL,
    FOREIGN KEY (credit_id) REFERENCES credits(id),
    FOREIGN KEY (type_id) REFERENCES dictionary(id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Створення таблиці plans з auto_increment
CREATE TABLE plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    period DATE NOT NULL,
    sum DECIMAL(10,2) NOT NULL,
    category_id INT NOT NULL,
    FOREIGN KEY (category_id) REFERENCES dictionary(id)
) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## Запуск

```bash
python run.py
```

Сервіс буде доступний за адресою: http://localhost:8000

## Структура БД

- **Users** - таблиця з інформацією про користувачів
  - `id` - унікальний для кожного запису
  - `login` - логін клієнта
  - `registration_date` - дата реєстрації клієнта

- **Credits** - таблиця з інформацією про кредити
  - `id` - унікальний для кожного запису
  - `user_id` - id клієнта з таблиці Users
  - `issuance_date` - дата видачі кредиту
  - `return_date` - крайня дата повернення кредиту
  - `actual_return_date` - реальна дата повернення кредиту
  - `body` - сума видачі
  - `percent` - нараховані відсотки

- **Dictionary** - таблиця-довідник категорій
  - `id` - унікальний для кожного запису
  - `name` - назва категорії

- **Plans** - таблиця з інформацією про плани
  - `id` - унікальний для кожного запису
  - `period` - місяць плану (перше число місяця)
  - `sum` - сума видачі/збору за планом
  - `category_id` - id категорії з таблиці Dictionary

- **Payments** - таблиця з інформацією про платежі
  - `id` - унікальний для кожного запису
  - `sum` - сума платежу
  - `payment_date` - дата платежу
  - `credit_id` - id кредиту з таблиці Credits
  - `type_id` - id типу платежу (тіло/відсотки) з таблиці Dictionary

## API Endpoints

### 1. Отримання інформації про кредити клієнта
```
GET /user_credits/{user_id}
```

Метод повертає список всіх кредитів клієнта з вказаним id і містить наступну інформацію:
- Дата видачі кредиту
- Булеве значення, чи закритий кредит (true - закритий, false - відкритий)
- Для закритих кредитів:
  - Дата повернення кредиту
  - Сума видачі
  - Нараховані відсотки
  - Сума платежів за кредитом
- Для відкритих кредитів:
  - Крайня дата повернення кредиту
  - Кількість днів прострочення кредиту
  - Сума видачі
  - Нараховані відсотки
  - Сума платежів по тілу
  - Сума платежів по відсотках

Приклад відповіді:
```json
{
  "credits": [
    {
      "issuance_date": "2020-06-23",
      "is_closed": true,
      "body": 3500.0,
      "percent": 1470.0,
      "actual_return_date": "2020-06-27",
      "total_payments": 0.0
    }
  ]
}
```

### 2. Завантаження планів на новий місяць
```
POST /plans_insert
Content-Type: multipart/form-data
file: Excel-файл
```

Метод приймає Excel-файл з інформацією про плани на новий місяць і:
- Перевіряє наявність у БД плану з місяцем та категорією з файлу
- Перевіряє правильність заповнення місяця плану (має бути вказано перше число місяця)
- Перевіряє, що стовпець суми не містить пустих значень
- За відсутності помилок вносить дані в таблицю Plans

### 3. Отримання інформації про виконання планів
```
GET /plans_performance/{check_date}
```

Метод приймає дату, станом на яку перевіряється виконання планів, і повертає:
- Місяць плану
- Категорія плану
- Сума з плану
- Сума виданих кредитів (для категорії "видача") або сума платежів (для категорії "збір")
- Відсоток виконання плану

### 4. Отримання зведеної інформації за рік
```
GET /year_performance/{year}
```

Метод приймає рік і повертає зведену інформацію по місяцях:
- Місяць і рік
- Кількість видач за місяць
- Сума з плану по видачам на місяць
- Сума видач за місяць
- Відсоток виконання плану по видачам
- Кількість платежів за місяць
- Сума з плану по збору за місяць
- Сума платежів за місяць
- Відсоток виконання плану по збору
- Відсоток суми видач за місяць від суми видач за рік
- Відсоток суми платежів за місяць від суми платежів за рік

## Формат даних

### Excel-файл для завантаження планів
- month: Дата (перше число місяця)
- category: Категорія (Видача/Збір)
- sum: Сума (число більше 0)
 
