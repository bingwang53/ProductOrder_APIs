from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_list_products_pagination_and_sorting():
    response = client.get("/products", params={"page": 1, "page_size": 2, "sort_by": "price", "sort_order": "desc"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["price"] >= data[1]["price"]


def test_create_and_get_order():
    payload = {
        "customer_name": "Taylor Green",
        "status": "processing",
        "items": [
            {"product_id": 1, "quantity": 1},
            {"product_id": 2, "quantity": 3},
        ],
    }

    create_response = client.post("/orders", json=payload)
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["total_amount"] > 0
    assert len(created["items"]) == 2

    order_id = created["id"]
    get_response = client.get(f"/orders/{order_id}")
    assert get_response.status_code == 200
    fetched = get_response.json()
    assert fetched["customer_name"] == "Taylor Green"
    assert fetched["status"] == "processing"

