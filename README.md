# Product Order APIs Demo Guide

This project demonstrates an online order flow where a **PHP app** sends order data to a **FastAPI backend**, and the backend stores/updates data in **MySQL (XAMPP)**.

## Demo Flow

1. Customer places order in PHP app.
2. PHP app sends JSON to FastAPI: `POST /orders`.
3. FastAPI validates payload, calculates total, writes to MySQL.
4. Operations team updates order status via API: `PUT /orders/{id}`.
5. You verify results in Swagger and phpMyAdmin.

## Tech Stack

- FastAPI + Uvicorn
- SQLAlchemy + PyMySQL
- MySQL from XAMPP
- Optional PHP app (or local PHP script) as order source

## Project APIs

- `GET /products`
- `GET /products/{id}`
- `POST /products`
- `PUT /products/{id}`
- `DELETE /products/{id}`
- `GET /orders`
- `GET /orders/{id}`
- `POST /orders`
- `PUT /orders/{id}`
- `DELETE /orders/{id}`

Pagination/sorting supported on list endpoints:
- `page`, `page_size`
- `sort_by`, `sort_order`

## 1. Start MySQL (XAMPP)

1. Open XAMPP Control Panel.
2. Start **MySQL**.
3. Confirm port `3306` is listening.

## 2. Configure and Run FastAPI

From project root:

```powershell
cd C:\Users\BingWang\ProductOrder_APIs
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create `.env` (or copy from `.env.example`):

```env
DATABASE_URL=mysql+pymysql://root:@127.0.0.1:3306/product_order_db
```

If your MySQL `root` has a password:

```env
DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@127.0.0.1:3306/product_order_db
```

Run API:

```powershell
python -m uvicorn main:app --reload
```

Open:
- Swagger UI: `http://127.0.0.1:8000/docs`
- Health/root: `http://127.0.0.1:8000/`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

## View APIs Locally

Use one of these URLs in your browser:

- `http://127.0.0.1:8000/docs` (interactive Swagger)
- `http://127.0.0.1:8000/redoc` (ReDoc docs)
- `http://127.0.0.1:8000/openapi.json` (raw API schema)

Important:
- `127.0.0.0` is a network address and is not the correct local host URL for your app.
- Use `127.0.0.1` or `localhost` instead.

## 3. Demo: Send Online Order from PHP

Create a PHP file (example: `submit_order.php`) and run it from your PHP app/server.

```php
<?php
$payload = [
  "customer_name" => "Web Customer",
  "status" => "pending",
  "items" => [
    ["product_id" => 1, "quantity" => 1],
    ["product_id" => 2, "quantity" => 2]
  ]
];

$ch = curl_init("http://127.0.0.1:8000/orders");
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_HTTPHEADER, ["Content-Type: application/json"]);
curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload));

$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

echo "HTTP: " . $httpCode . PHP_EOL;
echo $response . PHP_EOL;
```

Expected result:
- HTTP `201`
- Response JSON contains `id`, `items`, and calculated `total_amount`

## 4. Demo: Backend Update API (Order Status)

After creating an order, update it:

```bash
curl -X PUT "http://127.0.0.1:8000/orders/1" \
  -H "Content-Type: application/json" \
  -d '{"status":"processing"}'
```

Then verify:

```bash
curl "http://127.0.0.1:8000/orders/1"
```

You can also do both from Swagger UI.

## 5. Verify in Database (phpMyAdmin)

In phpMyAdmin, check database `product_order_db`:
- `products`
- `orders`
- `order_items`

You should see:
- New row in `orders`
- Related rows in `order_items`
- Updated `status` after `PUT /orders/{id}`

## Useful Demo Queries

- List newest/highest orders:
  - `/orders?page=1&page_size=10&sort_by=total_amount&sort_order=desc`
- Filter by customer:
  - `/orders?customer_name=Web`
- Filter by status:
  - `/orders?status=processing`

## Test Suite

Run automated tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Troubleshooting

- `Can't connect to MySQL`:
  - Confirm XAMPP MySQL is running and credentials in `.env` are correct.
- `Unknown database`:
  - Start app once; it auto-creates `product_order_db`.
- `127.0.0.1:8000 not loading`:
  - Make sure Uvicorn is running in the active terminal.
- PHP request fails:
  - Ensure FastAPI base URL is correct (`http://127.0.0.1:8000`).
