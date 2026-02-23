from __future__ import annotations

import json
import os
from decimal import Decimal
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from sqlalchemy import DECIMAL, ForeignKey, Integer, String, create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PRODUCTS_FILE = DATA_DIR / "products.json"
ORDERS_FILE = DATA_DIR / "orders.json"
load_dotenv(BASE_DIR / ".env")
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:@127.0.0.1:3306/product_order_db")


class Base(DeclarativeBase):
    pass


class ProductModel(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    price: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False)


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    total_amount: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), nullable=False, default=0)
    items: Mapped[list[OrderItemModel]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItemModel(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    order: Mapped[OrderModel] = relationship(back_populates="items")


def build_engine(database_url: str):
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)


engine = build_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class ProductBase(BaseModel):
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    price: float = Field(gt=0)
    stock: int = Field(ge=0)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    category: str | None = Field(default=None, min_length=1)
    price: float | None = Field(default=None, gt=0)
    stock: int | None = Field(default=None, ge=0)


class Product(ProductBase):
    id: int

    model_config = {"from_attributes": True}


class OrderItem(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class OrderBase(BaseModel):
    customer_name: str = Field(min_length=1)
    status: Literal["pending", "processing", "shipped", "cancelled"] = "pending"
    items: list[OrderItem] = Field(min_length=1)


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    customer_name: str | None = Field(default=None, min_length=1)
    status: Literal["pending", "processing", "shipped", "cancelled"] | None = None
    items: list[OrderItem] | None = Field(default=None, min_length=1)


class Order(BaseModel):
    id: int
    customer_name: str
    status: str
    items: list[OrderItem]
    total_amount: float


def read_json(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return data if isinstance(data, list) else []


def ensure_mysql_database_exists() -> None:
    url = make_url(DATABASE_URL)
    if not url.get_backend_name().startswith("mysql") or not url.database:
        return

    db_name = url.database
    admin_url = url.set(database="mysql").render_as_string(hide_password=False)
    admin_engine = create_engine(admin_url, pool_pre_ping=True)
    try:
        with admin_engine.begin() as connection:
            connection.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
    finally:
        admin_engine.dispose()


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI(title="Product Order API", version="1.1.0", openapi_version="3.0.3")


def decimal_to_float(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01")))


def get_product_or_404(db: Session, product_id: int) -> ProductModel:
    product = db.get(ProductModel, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


def get_order_or_404(db: Session, order_id: int) -> OrderModel:
    order = db.get(OrderModel, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def calculate_total(db: Session, items: list[OrderItem]) -> Decimal:
    total = Decimal("0.00")
    for item in items:
        product = db.get(ProductModel, item.product_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        total += Decimal(product.price) * item.quantity
    return total.quantize(Decimal("0.01"))


def order_to_response(order: OrderModel) -> Order:
    return Order(
        id=order.id,
        customer_name=order.customer_name,
        status=order.status,
        items=[OrderItem(product_id=item.product_id, quantity=item.quantity) for item in order.items],
        total_amount=decimal_to_float(order.total_amount),
    )


def seed_initial_data(db: Session) -> None:
    has_product = db.execute(select(ProductModel.id).limit(1)).scalar_one_or_none()
    if has_product:
        return

    for item in read_json(PRODUCTS_FILE):
        db.add(
            ProductModel(
                id=item.get("id"),
                name=item["name"],
                category=item["category"],
                price=Decimal(str(item["price"])),
                stock=item["stock"],
            )
        )
    db.commit()

    for item in read_json(ORDERS_FILE):
        order = OrderModel(
            id=item.get("id"),
            customer_name=item["customer_name"],
            status=item.get("status", "pending"),
            total_amount=Decimal(str(item.get("total_amount", 0))),
        )
        for order_item in item.get("items", []):
            order.items.append(
                OrderItemModel(
                    product_id=order_item["product_id"],
                    quantity=order_item["quantity"],
                )
            )
        db.add(order)
    db.commit()


@app.on_event("startup")
def startup() -> None:
    ensure_mysql_database_exists()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_initial_data(db)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Product Order API is running with MySQL"}


@app.get("/products", response_model=list[Product])
def list_products(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: Literal["id", "name", "category", "price", "stock"] = Query(default="id"),
    sort_order: Literal["asc", "desc"] = Query(default="asc"),
    db: Session = Depends(get_db),
) -> list[ProductModel]:
    sort_column_map = {
        "id": ProductModel.id,
        "name": ProductModel.name,
        "category": ProductModel.category,
        "price": ProductModel.price,
        "stock": ProductModel.stock,
    }
    sort_column = sort_column_map[sort_by]
    order_clause = sort_column.desc() if sort_order == "desc" else sort_column.asc()
    offset = (page - 1) * page_size
    return (
        db.execute(select(ProductModel).order_by(order_clause).offset(offset).limit(page_size))
        .scalars()
        .all()
    )


@app.get("/products/{product_id}", response_model=Product)
def get_product(product_id: int, db: Session = Depends(get_db)) -> ProductModel:
    return get_product_or_404(db, product_id)


@app.post("/products", response_model=Product, status_code=201)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)) -> ProductModel:
    product = ProductModel(
        name=payload.name,
        category=payload.category,
        price=Decimal(str(payload.price)).quantize(Decimal("0.01")),
        stock=payload.stock,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@app.put("/products/{product_id}", response_model=Product)
def update_product(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db)) -> ProductModel:
    product = get_product_or_404(db, product_id)
    updates = payload.model_dump(exclude_unset=True)
    if "price" in updates:
        updates["price"] = Decimal(str(updates["price"])).quantize(Decimal("0.01"))
    for field, value in updates.items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@app.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)) -> None:
    product = get_product_or_404(db, product_id)
    referenced = db.execute(
        select(OrderItemModel.id).where(OrderItemModel.product_id == product_id).limit(1)
    ).scalar_one_or_none()
    if referenced:
        raise HTTPException(status_code=409, detail="Product is referenced by existing orders")
    db.delete(product)
    db.commit()


@app.get("/orders", response_model=list[Order])
def list_orders(
    customer_name: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: Literal["id", "customer_name", "status", "total_amount"] = Query(default="id"),
    sort_order: Literal["asc", "desc"] = Query(default="asc"),
    db: Session = Depends(get_db),
) -> list[Order]:
    sort_column_map = {
        "id": OrderModel.id,
        "customer_name": OrderModel.customer_name,
        "status": OrderModel.status,
        "total_amount": OrderModel.total_amount,
    }
    sort_column = sort_column_map[sort_by]
    order_clause = sort_column.desc() if sort_order == "desc" else sort_column.asc()

    query = select(OrderModel).order_by(order_clause)
    if customer_name:
        query = query.where(OrderModel.customer_name.ilike(f"%{customer_name}%"))
    if status:
        query = query.where(OrderModel.status == status)
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    orders = db.execute(query).scalars().all()
    return [order_to_response(order) for order in orders]


@app.get("/orders/{order_id}", response_model=Order)
def get_order(order_id: int, db: Session = Depends(get_db)) -> Order:
    return order_to_response(get_order_or_404(db, order_id))


@app.post("/orders", response_model=Order, status_code=201)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)) -> Order:
    total = calculate_total(db, payload.items)
    order = OrderModel(
        customer_name=payload.customer_name,
        status=payload.status,
        total_amount=total,
        items=[
            OrderItemModel(product_id=item.product_id, quantity=item.quantity)
            for item in payload.items
        ],
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order_to_response(order)


@app.put("/orders/{order_id}", response_model=Order)
def update_order(order_id: int, payload: OrderUpdate, db: Session = Depends(get_db)) -> Order:
    order = get_order_or_404(db, order_id)
    updates = payload.model_dump(exclude_unset=True)

    if "customer_name" in updates:
        order.customer_name = updates["customer_name"]
    if "status" in updates:
        order.status = updates["status"]

    if "items" in updates:
        new_items = [
            OrderItem(**item) if isinstance(item, dict) else item for item in updates["items"]
        ]
        order.total_amount = calculate_total(db, new_items)
        order.items.clear()
        order.items.extend(
            [OrderItemModel(product_id=item.product_id, quantity=item.quantity) for item in new_items]
        )

    db.commit()
    db.refresh(order)
    return order_to_response(order)


@app.delete("/orders/{order_id}", status_code=204)
def delete_order(order_id: int, db: Session = Depends(get_db)) -> None:
    order = get_order_or_404(db, order_id)
    db.delete(order)
    db.commit()
