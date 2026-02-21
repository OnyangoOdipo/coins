from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models import Store, Product, ScrapeLog
from ..scrape_service import scrape_all_stores, SCRAPERS

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("/")
async def list_stores(db: Session = Depends(get_db)):
    stores = db.query(Store).filter_by(is_active=True).all()
    result = []
    for store in stores:
        product_count = db.query(func.count(Product.id)).filter_by(store_id=store.id).scalar()
        result.append({
            "id": store.id,
            "name": store.name,
            "slug": store.slug,
            "color": store.color,
            "logo_url": store.logo_url,
            "product_count": product_count,
        })
    return result


@router.get("/stats")
async def scrape_stats(db: Session = Depends(get_db)):
    """Dashboard stats: total products, last scrape time per store."""
    stats = []
    stores = db.query(Store).all()
    for store in stores:
        total = db.query(func.count(Product.id)).filter_by(store_id=store.id).scalar()
        last_scraped = (
            db.query(func.max(Product.last_scraped))
            .filter_by(store_id=store.id)
            .scalar()
        )
        stats.append({
            "store": store.name,
            "slug": store.slug,
            "color": store.color,
            "total_products": total,
            "last_scraped": last_scraped,
        })
    return stats
