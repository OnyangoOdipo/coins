from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    shopping_lists = relationship("ShoppingList", back_populates="user")


class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(50), unique=True, nullable=False)
    base_url = Column(String(255))
    logo_url = Column(String(500))
    color = Column(String(20), default="#000000")  # brand color for UI
    is_active = Column(Boolean, default=True)

    products = relationship("Product", back_populates="store")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False)

    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    name = Column(String(500), nullable=False)
    brand = Column(String(200))
    normalized_name = Column(String(500))  # cleaned name for matching across stores
    sku = Column(String(200))
    url = Column(String(1000))
    image_url = Column(String(1000))
    current_price = Column(Float)
    original_price = Column(Float)  # price before discount
    unit = Column(String(50))       # e.g. "1kg", "500ml", "6-pack"
    in_stock = Column(Boolean, default=True)
    last_scraped = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    store = relationship("Store", back_populates="products")
    category = relationship("Category", back_populates="products")
    price_history = relationship("PriceHistory", back_populates="product")

    __table_args__ = (
        Index("ix_product_normalized_name", "normalized_name"),
        Index("ix_product_store_id", "store_id"),
    )


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    price = Column(Float, nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product", back_populates="price_history")

    __table_args__ = (
        Index("ix_price_history_product_id", "product_id"),
    )


class ShoppingList(Base):
    __tablename__ = "shopping_lists"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), default="My Shopping List")
    session_id = Column(String(100), nullable=True)  # deprecated
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="shopping_lists")
    items = relationship("ShoppingListItem", back_populates="shopping_list", cascade="all, delete-orphan")


class ShoppingListItem(Base):
    __tablename__ = "shopping_list_items"

    id = Column(Integer, primary_key=True)
    shopping_list_id = Column(Integer, ForeignKey("shopping_lists.id"), nullable=False)
    search_query = Column(String(300), nullable=False)  # what the user searched for
    quantity = Column(Integer, default=1)
    notes = Column(Text)

    shopping_list = relationship("ShoppingList", back_populates="items")


class ScrapeLog(Base):
    __tablename__ = "scrape_logs"

    id = Column(Integer, primary_key=True)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True))
    products_scraped = Column(Integer, default=0)
    status = Column(String(50), default="running")  # running, success, failed
    error_message = Column(Text)
