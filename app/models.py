# app/models.py
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, func, Index
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(255), nullable=False)  # original SKU text
    sku_lower = Column(String(255), nullable=False)  # created by migration / kept for SQLAlchemy
    name = Column(String(512), nullable=False)
    description = Column(Text)
    price_cents = Column(Integer)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

Index("uq_products_sku_lower", Product.sku_lower, unique=True)

class Webhook(Base):
    __tablename__ = "webhooks"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=True)
    url = Column(Text, nullable=False)
    event = Column(String(128), nullable=False)  # e.g., "import.completed"
    enabled = Column(Boolean, nullable=False, default=True)
    last_status = Column(String(128), nullable=True)
    last_response_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
