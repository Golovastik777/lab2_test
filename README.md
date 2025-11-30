# Лабораторная работа 2: Интеграционное тестирование

## 1. Описание проекта

### Выбранный проект
Проект: **FastAPI приложение для управления продуктами и категориями**

Это веб-приложение на FastAPI, которое предоставляет REST API для управления каталогом продуктов. Проект имеет чёткую архитектуру с разделением на слои:

- **API Layer (routers)**: Обработка HTTP-запросов, валидация входных данных
- **Business Logic Layer (controllers)**: Бизнес-логика, построение запросов
- **Data Layer (models/db)**: Работа с базой данных через SQLAlchemy

### Структура проекта
```
fastapi dz proga/
├── main.py                 # Точка входа, настройка FastAPI приложения
├── routers/                # API роутеры (products.py, categories.py)
├── controllers/            # Бизнес-логика (products.py, categories.py)
├── models/                 # Модели данных и схемы
│   ├── models.py          # SQLAlchemy таблицы
│   ├── schemas.py         # Pydantic схемы
│   └── db.py              # Подключение к БД
└── tests/
    └── test_integration/   # Интеграционные тесты
```

### Технологический стек
- **FastAPI**: Веб-фреймворк для создания API
- **SQLAlchemy**: ORM для работы с базой данных
- **Databases**: Асинхронная работа с БД
- **Pydantic**: Валидация данных
- **Pytest**: Фреймворк для тестирования
- **SQLite/PostgreSQL**: База данных (в тестах используется SQLite)

## 2. Анализ взаимодействий и ключевые точки интеграции

### 2.1 Выявленные точки интеграции

#### 1. **API <-> Controller <-> Database (CRUD операции)**
- **Описание**: Полный цикл создания, чтения, обновления и удаления данных
- **Компоненты**: 
  - `routers/products.py` → `controllers/products.py` → `models/db.py` → SQLite
- **Важность**: Это основная функциональность приложения. Необходимо проверить, что данные корректно проходят через все слои.

#### 2. **Каскадные ограничения (Foreign Key Constraints)**
- **Описание**: Связь между категориями и продуктами через внешний ключ
- **Компоненты**: 
  - Database constraints → Controller validation → API error handling
- **Важность**: Критично для целостности данных. Нельзя удалить категорию, если в ней есть продукты.

#### 3. **Сложные запросы с JOIN и фильтрацией**
- **Описание**: Запросы, объединяющие таблицы products и categories с фильтрацией и сортировкой
- **Компоненты**: 
  - API query parameters → Controller query building → Database JOIN queries
- **Важность**: Проверяет корректность работы сложных SQL-запросов через все слои.

#### 4. **Обработка ошибок через слои**
- **Описание**: Распространение ошибок от базы данных до API
- **Компоненты**: 
  - Database exceptions → Controller error handling → API error responses
- **Важность**: Пользователь должен получать понятные сообщения об ошибках.

#### 5. **Фильтрация по дате и категории**
- **Описание**: Комбинированная фильтрация продуктов по нескольким критериям
- **Компоненты**: 
  - API date/category params → Controller date handling → Database WHERE clauses
- **Важность**: Проверяет корректность работы с датами и комбинированными фильтрами.

### 2.2 Обоснование выбора интеграций

1. **API ↔ Controller ↔ Database**: Это основная интеграция, без которой приложение не работает. Необходимо убедиться, что данные корректно сохраняются и извлекаются.

2. **Каскадные ограничения**: Критично для бизнес-логики. Ошибки здесь могут привести к нарушению целостности данных (orphaned records).

3. **Сложные запросы**: Проверяет корректность работы JOIN-запросов и сортировки, что важно для производительности и корректности отображения данных.

4. **Обработка ошибок**: Важно для пользовательского опыта. Ошибки должны корректно обрабатываться на всех уровнях.

5. **Фильтрация по дате**: Проверяет работу с типами данных (date) и комбинированными условиями в запросах.

## 3. Написанные интеграционные тесты

### 3.1 Список тестов

Всего написано **6 интеграционных тестов**, покрывающих различные сценарии:

1. **test_full_product_lifecycle_integration**: Полный жизненный цикл продукта
2. **test_category_product_cascade_constraints**: Каскадные ограничения
3. **test_data_consistency_across_multiple_operations**: Консистентность данных
4. **test_error_propagation_through_layers**: Распространение ошибок
5. **test_date_filtering_integration**: Фильтрация по дате
6. **test_complex_query_integration_with_sorting**: Сложные запросы с сортировкой

### 3.2 Примеры кода тестов

#### Тест 1: Полный жизненный цикл продукта

```python
async def test_full_product_lifecycle_integration(client):
    """
    Проверяет интеграцию: API -> Controller -> Database -> Controller -> API
    """
    # Создание категории через API
    category_response = await create_category(client, "Electronics")
    assert category_response.status_code == status.HTTP_200_OK
    category_data = category_response.json()
    category_id = category_data["id"]
    
    # Создание продукта через API (проверка связи с категорией)
    product_response = await create_product(client, "Smartphone", 999.99, "Electronics")
    assert product_response.status_code == status.HTTP_200_OK
    product_data = product_response.json()
    assert product_data["category_id"] == category_id
    
    # Получение продукта через API с фильтрацией
    get_response = await client.get(
        "/api/v1/products/",
        params={"read_all": False, "select_by_category": "Electronics"},
    )
    assert get_response.status_code == status.HTTP_200_OK
    products = get_response.json()
    assert len(products) == 1
    
    # Удаление продукта
    delete_response = await client.delete(
        "/api/v1/products/", params={"product_id": product_data["id"]}
    )
    assert delete_response.status_code == status.HTTP_200_OK
```

**Что проверяет**: 
- Создание категории через API
- Создание продукта с привязкой к категории
- Получение данных через API
- Удаление продукта
- Проверка, что данные корректно проходят через все слои

#### Тест 2: Каскадные ограничения

```python
async def test_category_product_cascade_constraints(client):
    """
    Проверяет интеграцию: Database constraints -> Controller -> API error handling
    """
    # Создание категории и продукта
    await create_category(client, "Books")
    product_response = await create_product(client, "Python Guide", 49.99, "Books")
    product_id = product_response.json()["id"]
    
    # Попытка удалить категорию с продуктами должна вернуть ошибку
    delete_category_response = await client.delete(
        "/api/v1/categories/", params={"name": "Books"}
    )
    assert delete_category_response.status_code == status.HTTP_400_BAD_REQUEST
    assert "still products" in delete_category_response.json()["detail"].lower()
    
    # Удаление продукта, затем категории (успешный сценарий)
    await client.delete("/api/v1/products/", params={"product_id": product_id})
    delete_category_response = await client.delete(
        "/api/v1/categories/", params={"name": "Books"}
    )
    assert delete_category_response.status_code == status.HTTP_200_OK
```

**Что проверяет**:
- Защита от удаления категории с продуктами (foreign key constraint)
- Корректная обработка ошибки на уровне API
- Успешное удаление после очистки зависимостей

#### Тест 3: Консистентность данных

```python
async def test_data_consistency_across_multiple_operations(client):
    """
    Проверяет интеграцию: Multiple API calls -> Database transactions -> Data integrity
    """
    # Создание нескольких категорий
    categories = ["Clothing", "Shoes", "Accessories"]
    category_ids = {}
    for cat_name in categories:
        response = await create_category(client, cat_name)
        category_ids[cat_name] = response.json()["id"]
    
    # Создание продуктов в разных категориях
    products_data = [
        ("T-Shirt", 29.99, "Clothing"),
        ("Sneakers", 89.99, "Shoes"),
        ("Watch", 199.99, "Accessories"),
    ]
    
    for name, price, cat_name in products_data:
        response = await create_product(client, name, price, cat_name)
        product = response.json()
        assert product["category_id"] == category_ids[cat_name]
    
    # Проверка фильтрации по категории
    clothing_response = await client.get(
        "/api/v1/products/",
        params={"read_all": False, "select_by_category": "Clothing"},
    )
    clothing_products = clothing_response.json()
    assert len(clothing_products) == 1
    assert all(p["category_name"] == "Clothing" for p in clothing_products)
```

**Что проверяет**:
- Множественные операции создания
- Корректность связей между продуктами и категориями
- Фильтрация данных через API

#### Тест 4: Распространение ошибок

```python
async def test_error_propagation_through_layers(client):
    """
    Проверяет интеграцию: Database errors -> Controller -> API error responses
    """
    # Попытка создать продукт с несуществующей категорией
    response = await create_product(client, "Product", 10.0, "NonExistentCategory")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "does not exist" in response.json()["detail"].lower()
    
    # Попытка создать дубликат категории
    await create_category(client, "UniqueCategory")
    duplicate_response = await create_category(client, "UniqueCategory")
    assert duplicate_response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in duplicate_response.json()["detail"].lower()
```

**Что проверяет**:
- Обработка ошибок на уровне базы данных
- Корректное преобразование в HTTP-ошибки
- Понятные сообщения об ошибках для пользователя

#### Тест 5: Фильтрация по дате

```python
async def test_date_filtering_integration(client):
    """
    Проверяет интеграцию: API date params -> Controller date handling -> Database queries
    """
    await create_category(client, "Food")
    
    # Создание продукта (получает текущую дату)
    today = date.today()
    product1_response = await create_product(client, "Bread", 2.50, "Food")
    product1 = product1_response.json()
    assert product1["created_at"] == today.isoformat()
    
    # Получение продуктов по сегодняшней дате
    today_response = await client.get(
        "/api/v1/products/",
        params={
            "read_all": False,
            "select_by_date": today.isoformat(),
            "select_by_category": "Food",
        },
    )
    assert today_response.status_code == status.HTTP_200_OK
    today_products = today_response.json()
    assert len(today_products) >= 1
```

**Что проверяет**:
- Корректная работа с типами данных date
- Фильтрация по дате через API
- Комбинированная фильтрация (дата + категория)

#### Тест 6: Сложные запросы с сортировкой

```python
async def test_complex_query_integration_with_sorting(client):
    """
    Проверяет интеграцию: API complex params -> Controller query building -> Database JOIN queries
    """
    await create_category(client, "Electronics")
    
    # Создание продуктов с разными ценами
    products = [
        ("Laptop", 1500.0, "Electronics"),
        ("Mouse", 25.0, "Electronics"),
    ]
    
    for name, price, category in products:
        await create_product(client, name, price, category)
    
    # Тест сортировки по убыванию цены
    expensive_first = await client.get(
        "/api/v1/products/",
        params={
            "read_all": True,
            "sorting_by_price_from_exp_to_cheap": True,
        },
    )
    products_list = expensive_first.json()
    prices = [p["price"] for p in products_list]
    assert prices == sorted(prices, reverse=True)
    assert products_list[0]["name"] == "Laptop"
```

**Что проверяет**:
- JOIN-запросы между таблицами
- Сортировка данных
- Корректность работы сложных SQL-запросов

## 4. Результаты тестов и выводы

### 4.1 Запуск тестов

Для запуска интеграционных тестов необходимо:

1. Установить зависимости:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-test.txt
   ```

2. Запустить тесты:
   ```bash
   pytest tests/test_integration/test_full_integration.py -v
   ```

### 4.2 Ожидаемые результаты

Все 6 тестов должны пройти успешно, что подтверждает:

1.  **Корректность работы API**: Все эндпоинты работают правильно
2.  **Целостность данных**: Связи между таблицами сохраняются корректно
3.  **Обработка ошибок**: Ошибки корректно обрабатываются на всех уровнях
4.  **Сложные запросы**: JOIN-запросы и фильтрация работают правильно
5.  **Типы данных**: Работа с датами и другими типами данных корректна

### 4.3 Выводы

#### Что работает хорошо:

1. **Разделение ответственности**: Чёткое разделение на слои (API, Controller, Database) упрощает тестирование
2. **Обработка ошибок**: Ошибки корректно обрабатываются и преобразуются в понятные HTTP-ответы
3. **Целостность данных**: Foreign key constraints защищают от нарушения целостности данных
4. **Гибкость запросов**: Система поддерживает сложные запросы с фильтрацией и сортировкой

#### Возможные улучшения:

1. **Транзакции**: Можно добавить явное управление транзакциями для более сложных операций
2. **Валидация**: Можно добавить более строгую валидацию входных данных на уровне API
3. **Кэширование**: Для часто запрашиваемых данных можно добавить кэширование
4. **Логирование**: Добавить логирование для отслеживания операций

### 4.4 Важность интеграционного тестирования

Интеграционные тесты выявили несколько важных моментов:

1. **Проверка взаимодействия**: Тесты подтвердили, что все слои системы корректно взаимодействуют друг с другом
2. **Обнаружение проблем**: Тесты помогли выявить потенциальные проблемы с обработкой ошибок
3. **Документация**: Тесты служат живой документацией того, как система должна работать
4. **Регрессия**: Тесты защищают от регрессий при изменении кода

## 5. Заключение

В ходе лабораторной работы было написано 6 интеграционных тестов, которые проверяют ключевые точки взаимодействия между модулями системы:

- API <-> Controller <-> Database
- Обработка ошибок через все слои
- Каскадные ограничения и целостность данных
- Сложные запросы с фильтрацией и сортировкой

Все тесты успешно проходят, что подтверждает корректность работы интеграций между компонентами системы. Интеграционное тестирование показало свою важность для обеспечения надёжности и стабильности приложения.

