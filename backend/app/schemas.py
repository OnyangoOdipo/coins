from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class StoreOut(BaseModel):
    id: int
    name: str
    slug: str
    color: str
    logo_url: Optional[str]

    class Config:
        from_attributes = True


class ProductOut(BaseModel):
    id: int
    name: str
    normalized_name: Optional[str]
    current_price: Optional[float]
    original_price: Optional[float]
    unit: Optional[str]
    image_url: Optional[str]
    url: Optional[str]
    in_stock: bool
    last_scraped: Optional[datetime]
    store: StoreOut

    class Config:
        from_attributes = True


class PriceHistoryOut(BaseModel):
    price: float
    recorded_at: datetime

    class Config:
        from_attributes = True


class PriceCompareResult(BaseModel):
    store: StoreOut
    cheapest_product: ProductOut

    class Config:
        from_attributes = True
