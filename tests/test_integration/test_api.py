from datetime import date

import pytest
from starlette import status


pytestmark = pytest.mark.asyncio


async def create_category(client, name: str):
    return await client.post("/api/v1/categories/", params={"name": name})


async def create_product(client, name: str, price: float, category_name: str):
    return await client.post(
        "/api/v1/products/",
        params={"name": name, "price": price, "category_name": category_name},
    )


async def test_category_creation_and_listing(client):
    create_response = await create_category(client, "Electronics")
    assert create_response.status_code == status.HTTP_200_OK
    created_category = create_response.json()
    assert created_category["name"] == "Electronics"

    list_response = await client.get("/api/v1/categories/")
    assert list_response.status_code == status.HTTP_200_OK
    categories = list_response.json()
    assert len(categories) == 1
    assert categories[0]["name"] == "Electronics"


async def test_duplicate_category_creation_returns_400(client):
    await create_category(client, "Groceries")
    duplicate_response = await create_category(client, "Groceries")
    assert duplicate_response.status_code == status.HTTP_400_BAD_REQUEST
    assert duplicate_response.json()["detail"] == "Category already exists"


async def test_product_creation_and_sorted_listing(client):
    await create_category(client, "Tech")
    await create_product(client, "Laptop", 1500.0, "Tech")
    await create_product(client, "Mouse", 25.0, "Tech")

    response = await client.get(
        "/api/v1/products/",
        params={"read_all": True, "sorting_by_price_from_exp_to_cheap": True},
    )
    assert response.status_code == status.HTTP_200_OK
    products = response.json()
    assert len(products) == 2
    assert products[0]["name"] == "Laptop"
    assert products[0]["price"] == pytest.approx(1500.0)
    assert products[1]["name"] == "Mouse"


async def test_filter_products_by_date_and_category(client):
    await create_category(client, "Books")
    await create_product(client, "Novel", 20.0, "Books")
    today = date.today().isoformat()

    response = await client.get(
        "/api/v1/products/",
        params={
            "read_all": False,
            "select_by_category": "Books",
            "select_by_date": today,
        },
    )
    assert response.status_code == status.HTTP_200_OK
    products = response.json()
    assert len(products) == 1
    assert products[0]["name"] == "Novel"


async def test_product_creation_without_category_returns_404(client):
    response = await create_product(client, "Camera", 300.0, "Missing")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Category does not exist"


async def test_cannot_delete_category_with_products(client):
    await create_category(client, "Appliances")
    create_product_response = await create_product(client, "Blender", 99.0, "Appliances")
    product_id = create_product_response.json()["id"]

    delete_category_response = await client.delete(
        "/api/v1/categories/", params={"name": "Appliances"}
    )
    assert delete_category_response.status_code == status.HTTP_400_BAD_REQUEST
    assert (
        delete_category_response.json()["detail"]
        == "There are still products in the category"
    )

    delete_product_response = await client.delete(
        "/api/v1/products/", params={"product_id": product_id}
    )
    assert delete_product_response.status_code == status.HTTP_200_OK

    final_delete_category_response = await client.delete(
        "/api/v1/categories/", params={"name": "Appliances"}
    )
    assert final_delete_category_response.status_code == status.HTTP_200_OK

