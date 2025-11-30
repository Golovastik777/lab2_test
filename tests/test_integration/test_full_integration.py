"""
Интеграционные тесты для проверки взаимодействия между модулями системы:
- API (routers) <-> Controllers <-> Database
- Проверка целостности данных и бизнес-логики
"""
from datetime import date, timedelta

import pytest
from starlette import status


pytestmark = pytest.mark.asyncio


async def create_category(client, name: str):
    """Вспомогательная функция для создания категории"""
    return await client.post("/api/v1/categories/", params={"name": name})


async def create_product(client, name: str, price: float, category_name: str):
    """Вспомогательная функция для создания продукта"""
    return await client.post(
        "/api/v1/products/",
        params={"name": name, "price": price, "category_name": category_name},
    )


async def test_full_product_lifecycle_integration(client):
    """
    Тест 1: Полный жизненный цикл продукта через все слои системы
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
    assert product_data["name"] == "Smartphone"
    assert product_data["price"] == pytest.approx(999.99)
    assert product_data["category_id"] == category_id
    assert product_data["category_name"] == "Electronics"
    
    # Получение продукта через API с фильтрацией по категории
    get_response = await client.get(
        "/api/v1/products/",
        params={
            "read_all": False,
            "select_by_category": "Electronics",
        },
    )
    assert get_response.status_code == status.HTTP_200_OK
    products = get_response.json()
    assert len(products) == 1
    assert products[0]["id"] == product_data["id"]
    
    # Удаление продукта
    delete_response = await client.delete(
        "/api/v1/products/", params={"product_id": product_data["id"]}
    )
    assert delete_response.status_code == status.HTTP_200_OK
    
    # Проверка, что продукт удалён (попытка получить его должна вернуть пустой список)
    verify_response = await client.get(
        "/api/v1/products/",
        params={
            "read_all": False,
            "select_by_category": "Electronics",
        },
    )
    assert verify_response.status_code == status.HTTP_200_OK
    assert len(verify_response.json()) == 0


async def test_category_product_cascade_constraints(client):
    """
    Тест 2: Проверка каскадных ограничений между категориями и продуктами
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
    
    # Проверка, что категория и продукт всё ещё существуют
    categories_response = await client.get("/api/v1/categories/")
    categories = categories_response.json()
    assert any(cat["name"] == "Books" for cat in categories)
    
    products_response = await client.get(
        "/api/v1/products/",
        params={"read_all": True},
    )
    products = products_response.json()
    assert any(p["id"] == product_id for p in products)
    
    # Удаление продукта, затем категории (успешный сценарий)
    await client.delete("/api/v1/products/", params={"product_id": product_id})
    delete_category_response = await client.delete(
        "/api/v1/categories/", params={"name": "Books"}
    )
    assert delete_category_response.status_code == status.HTTP_200_OK


async def test_data_consistency_across_multiple_operations(client):
    """
    Тест 3: Проверка консистентности данных при множественных операциях
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
        ("Jeans", 59.99, "Clothing"),
    ]
    
    created_products = []
    for name, price, cat_name in products_data:
        response = await create_product(client, name, price, cat_name)
        assert response.status_code == status.HTTP_200_OK
        product = response.json()
        assert product["category_name"] == cat_name
        assert product["category_id"] == category_ids[cat_name]
        created_products.append(product)
    
    # Проверка фильтрации по категории
    clothing_response = await client.get(
        "/api/v1/products/",
        params={"read_all": False, "select_by_category": "Clothing"},
    )
    clothing_products = clothing_response.json()
    assert len(clothing_products) == 2
    assert all(p["category_name"] == "Clothing" for p in clothing_products)
    
    # Проверка сортировки по цене
    sorted_response = await client.get(
        "/api/v1/products/",
        params={
            "read_all": True,
            "sorting_by_price_from_exp_to_cheap": True,
        },
    )
    sorted_products = sorted_response.json()
    prices = [p["price"] for p in sorted_products]
    assert prices == sorted(prices, reverse=True)


async def test_error_propagation_through_layers(client):
    """
    Тест 4: Проверка распространения ошибок через все слои системы
    Проверяет интеграцию: Database errors -> Controller -> API error responses
    """
    # Попытка создать продукт с несуществующей категорией
    response = await create_product(client, "Product", 10.0, "NonExistentCategory")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "does not exist" in response.json()["detail"].lower()
    
    # Попытка удалить несуществующий продукт
    delete_response = await client.delete(
        "/api/v1/products/", params={"product_id": 99999}
    )
    assert delete_response.status_code == status.HTTP_404_NOT_FOUND
    assert "does not exist" in delete_response.json()["detail"].lower()
    
    # Попытка удалить несуществующую категорию
    delete_cat_response = await client.delete(
        "/api/v1/categories/", params={"name": "NonExistent"}
    )
    assert delete_cat_response.status_code == status.HTTP_400_BAD_REQUEST
    
    # Попытка создать дубликат категории
    await create_category(client, "UniqueCategory")
    duplicate_response = await create_category(client, "UniqueCategory")
    assert duplicate_response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in duplicate_response.json()["detail"].lower()


async def test_date_filtering_integration(client):
    """
    Тест 5: Проверка фильтрации по дате через все слои
    Проверяет интеграцию: API date params -> Controller date handling -> Database queries
    """
    # Создание категории
    await create_category(client, "Food")
    
    # Создание продуктов (они получат текущую дату)
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    # Создаём продукт сегодня
    product1_response = await create_product(client, "Bread", 2.50, "Food")
    product1 = product1_response.json()
    assert product1["created_at"] == today.isoformat()
    
    # Попытка получить продукты по сегодняшней дате
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
    assert all(p["created_at"] == today.isoformat() for p in today_products)
    
    # Попытка получить продукты по вчерашней дате (должно быть пусто)
    yesterday_response = await client.get(
        "/api/v1/products/",
        params={
            "read_all": False,
            "select_by_date": yesterday.isoformat(),
            "select_by_category": "Food",
        },
    )
    assert yesterday_response.status_code == status.HTTP_200_OK
    yesterday_products = yesterday_response.json()
    assert len(yesterday_products) == 0


async def test_complex_query_integration_with_sorting(client):
    """
    Тест 6: Проверка сложных запросов с фильтрацией и сортировкой
    Проверяет интеграцию: API complex params -> Controller query building -> Database JOIN queries
    """
    # Создание категорий и продуктов
    await create_category(client, "Electronics")
    await create_category(client, "Furniture")
    
    # Создание продуктов с разными ценами
    products = [
        ("Laptop", 1500.0, "Electronics"),
        ("Table", 200.0, "Furniture"),
        ("Mouse", 25.0, "Electronics"),
        ("Chair", 150.0, "Furniture"),
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
    assert expensive_first.status_code == status.HTTP_200_OK
    products_list = expensive_first.json()
    assert len(products_list) == 4
    prices = [p["price"] for p in products_list]
    assert prices == sorted(prices, reverse=True)
    assert products_list[0]["name"] == "Laptop"
    
    # Тест сортировки по возрастанию цены
    cheap_first = await client.get(
        "/api/v1/products/",
        params={
            "read_all": True,
            "sorting_by_price_from_exp_to_cheap": False,
        },
    )
    assert cheap_first.status_code == status.HTTP_200_OK
    products_list_asc = cheap_first.json()
    prices_asc = [p["price"] for p in products_list_asc]
    assert prices_asc == sorted(prices_asc)
    assert products_list_asc[0]["name"] == "Mouse"

