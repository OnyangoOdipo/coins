from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from typing import Optional
from ..database import get_db
from ..models import Product, Store, PriceHistory
from ..schemas import ProductOut, PriceCompareResult, PriceHistoryOut
from ..matcher import match_products
from ..scrape_service import smart_scrape

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/search")
async def search_products(
    q: str = Query(..., min_length=1),
    live: bool = False,
    db: Session = Depends(get_db),
):
    """
    Search for products across all stores.
    Regular search: cached DB data + fast Carrefour API only.
    Live search (live=true): also scrapes Naivas/Quickmart via Playwright (~30s).
    """
    await smart_scrape(q, db, fast_only=not live)

    # Word-level search: require ALL words to match
    words = q.lower().split()
    word_conditions = []
    for word in words:
        pattern = f"%{word}%"
        word_conditions.append(
            or_(
                func.lower(Product.name).like(pattern),
                func.lower(Product.normalized_name).like(pattern),
            )
        )

    products = (
        db.query(Product, Store)
        .join(Store, Product.store_id == Store.id)
        .filter(
            Product.in_stock == True,
            and_(*word_conditions),
        )
        .order_by(Product.current_price.asc())
        .limit(100)
        .all()
    )

    results = []
    for product, store in products:
        results.append({
            "id": product.id,
            "name": product.name,
            "normalized_name": product.normalized_name,
            "current_price": product.current_price,
            "original_price": product.original_price,
            "unit": product.unit,
            "image_url": product.image_url,
            "url": product.url,
            "in_stock": product.in_stock,
            "last_scraped": product.last_scraped,
            "store": {
                "id": store.id,
                "name": store.name,
                "slug": store.slug,
                "color": store.color,
                "logo_url": store.logo_url,
            },
        })

    return {"query": q, "count": len(results), "results": results}


@router.get("/compare")
async def compare_prices(
    q: str = Query(..., min_length=1),
    live: bool = False,
    db: Session = Depends(get_db),
):
    """
    Compare prices for a product across all stores.
    Regular: cached DB data + fast Carrefour API.
    Live (live=true): also scrapes Naivas/Quickmart via Playwright.
    """
    await smart_scrape(q, db, fast_only=not live)

    words = q.lower().split()
    word_conditions = []
    for word in words:
        pattern = f"%{word}%"
        word_conditions.append(
            or_(
                func.lower(Product.name).like(pattern),
                func.lower(Product.normalized_name).like(pattern),
            )
        )

    rows = (
        db.query(Product, Store)
        .join(Store, Product.store_id == Store.id)
        .filter(
            Product.in_stock == True,
            and_(*word_conditions),
            Product.current_price.isnot(None),
        )
        .order_by(Product.current_price.asc())
        .all()
    )

    if not rows:
        return {"query": q, "groups": [], "summary": None}

    # Build flat product list with store info for the matcher
    flat_products = []
    store_map = {}
    for product, store in rows:
        store_map[store.slug] = {
            "name": store.name,
            "slug": store.slug,
            "color": store.color,
            "logo_url": store.logo_url,
        }
        flat_products.append({
            "id": product.id,
            "name": product.name,
            "normalized_name": product.normalized_name,
            "current_price": product.current_price,
            "original_price": product.original_price,
            "unit": product.unit,
            "image_url": product.image_url,
            "url": product.url,
            "store": store.slug,
            "store_slug": store.slug,
        })

    # Use Groq to group equivalent products across stores
    raw_groups = match_products(q, flat_products)

    # Build comparison groups — each group = one product across stores
    groups = []
    for group in raw_groups:
        stores = []
        seen_stores = set()
        for p in sorted(group["products"], key=lambda x: x["current_price"] or float("inf")):
            slug = p["store_slug"]
            # Keep cheapest per store within this group
            if slug in seen_stores:
                continue
            seen_stores.add(slug)
            stores.append({
                "store": store_map.get(slug, {"name": slug, "slug": slug}),
                "product": {
                    "id": p["id"],
                    "name": p["name"],
                    "current_price": p["current_price"],
                    "original_price": p.get("original_price"),
                    "unit": p.get("unit"),
                    "image_url": p.get("image_url"),
                    "url": p.get("url"),
                },
            })

        if not stores:
            continue

        # Calculate savings within this group
        prices = [s["product"]["current_price"] for s in stores if s["product"]["current_price"]]
        cheapest_price = min(prices) if prices else None
        most_expensive = max(prices) if prices else None

        savings = None
        if cheapest_price and most_expensive and most_expensive > cheapest_price:
            savings = {
                "amount": round(most_expensive - cheapest_price, 2),
                "percentage": round(((most_expensive - cheapest_price) / most_expensive) * 100, 1),
            }

        # Pick the image from the product with the best image available
        image_url = None
        for s in stores:
            if s["product"].get("image_url"):
                image_url = s["product"]["image_url"]
                break

        groups.append({
            "label": group["label"],
            "image_url": image_url,
            "stores": stores,
            "store_count": len(stores),
            "cheapest": {
                "store_slug": stores[0]["store"]["slug"],
                "store_name": stores[0]["store"]["name"],
                "price": cheapest_price,
            } if stores else None,
            "savings": savings,
        })

    # Sort: multi-store groups first, then by savings descending, then by price
    groups.sort(key=lambda g: (
        -g["store_count"],
        -(g["savings"]["amount"] if g["savings"] else 0),
        g["cheapest"]["price"] if g["cheapest"] else float("inf"),
    ))

    # Build summary
    multi_store = [g for g in groups if g["store_count"] > 1]
    best_saving = None
    if multi_store:
        with_savings = [g for g in multi_store if g["savings"]]
        if with_savings:
            top = max(with_savings, key=lambda g: g["savings"]["amount"])
            best_saving = {
                "label": top["label"],
                "amount": top["savings"]["amount"],
                "percentage": top["savings"]["percentage"],
                "store": top["cheapest"]["store_name"],
            }

    summary = {
        "total_groups": len(groups),
        "multi_store_groups": len(multi_store),
        "best_saving": best_saving,
    }

    return {
        "query": q,
        "groups": groups,
        "summary": summary,
    }


@router.get("/{product_id}/history")
async def price_history(product_id: int, db: Session = Depends(get_db)):
    """Get price history for a specific product."""
    product = db.query(Product).filter_by(id=product_id).first()
    if not product:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Product not found")

    history = (
        db.query(PriceHistory)
        .filter_by(product_id=product_id)
        .order_by(PriceHistory.recorded_at.asc())
        .all()
    )

    return {
        "product_id": product_id,
        "product_name": product.name,
        "history": [
            {"price": h.price, "recorded_at": h.recorded_at}
            for h in history
        ],
    }
