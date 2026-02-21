from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from typing import Optional
from pydantic import BaseModel
from ..database import get_db
from ..models import ShoppingList, ShoppingListItem, Product, Store, User
from ..matcher import match_products
from ..scrape_service import smart_scrape
from ..auth import get_current_user

router = APIRouter(prefix="/lists", tags=["shopping-lists"])


class ItemIn(BaseModel):
    search_query: str
    quantity: int = 1
    notes: Optional[str] = None


class ListCreate(BaseModel):
    name: str = "My Shopping List"


@router.post("/")
async def create_list(
    data: ListCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sl = ShoppingList(name=data.name, user_id=user.id)
    db.add(sl)
    db.commit()
    db.refresh(sl)
    return {"id": sl.id, "name": sl.name}


@router.get("/")
async def get_my_lists(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all lists for the authenticated user."""
    lists = (
        db.query(ShoppingList)
        .filter_by(user_id=user.id)
        .order_by(ShoppingList.updated_at.desc())
        .all()
    )
    return [
        {
            "id": sl.id,
            "name": sl.name,
            "item_count": len(sl.items),
            "updated_at": sl.updated_at,
        }
        for sl in lists
    ]


@router.get("/{list_id}")
async def get_list(
    list_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sl = db.query(ShoppingList).filter_by(id=list_id, user_id=user.id).first()
    if not sl:
        raise HTTPException(status_code=404, detail="List not found")
    return {
        "id": sl.id,
        "name": sl.name,
        "items": [
            {"id": i.id, "search_query": i.search_query, "quantity": i.quantity, "notes": i.notes}
            for i in sl.items
        ],
    }


@router.post("/{list_id}/items")
async def add_item(
    list_id: int,
    item: ItemIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sl = db.query(ShoppingList).filter_by(id=list_id, user_id=user.id).first()
    if not sl:
        raise HTTPException(status_code=404, detail="List not found")
    new_item = ShoppingListItem(
        shopping_list_id=list_id,
        search_query=item.search_query,
        quantity=item.quantity,
        notes=item.notes,
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return {"id": new_item.id, "search_query": new_item.search_query}


@router.delete("/{list_id}/items/{item_id}")
async def remove_item(
    list_id: int,
    item_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sl = db.query(ShoppingList).filter_by(id=list_id, user_id=user.id).first()
    if not sl:
        raise HTTPException(status_code=404, detail="List not found")
    item = db.query(ShoppingListItem).filter_by(id=item_id, shopping_list_id=list_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return {"ok": True}


@router.get("/{list_id}/optimize")
async def optimize_list(
    list_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    The killer feature: given a shopping list, figure out the cheapest
    combination of stores to buy everything from. Also shows single-store totals.
    Auto-scrapes any stores missing products for the list items.
    """
    sl = db.query(ShoppingList).filter_by(id=list_id, user_id=user.id).first()
    if not sl:
        raise HTTPException(status_code=404, detail="List not found")

    if not sl.items:
        return {"list_id": list_id, "items": [], "store_totals": {}, "best_plan": None}

    # Auto-scrape: only use fast sources (Carrefour API) to avoid
    # blocking on slow Playwright scrapes for Naivas/Quickmart
    for item in sl.items:
        await smart_scrape(item.search_query, db, fast_only=True)

    stores = {s.slug: s for s in db.query(Store).all()}

    item_results = []
    for item in sl.items:
        # Split query into words and require ALL words to match
        # e.g. "sugar 1kg" -> products must contain BOTH "sugar" AND "1kg"
        words = item.search_query.lower().split()
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

        # Build flat list for the matcher
        flat = []
        for product, store in rows:
            flat.append({
                "name": product.name,
                "normalized_name": product.normalized_name,
                "current_price": product.current_price,
                "unit": product.unit,
                "image_url": product.image_url,
                "url": product.url,
                "store": store.slug,
                "store_slug": store.slug,
                "store_name": store.name,
                "store_color": store.color,
            })

        # Use Groq to find the best-matching product group for this query
        groups = match_products(item.search_query, flat)

        # Pick the group with the most store coverage (best cross-store match)
        best_group = max(groups, key=lambda g: len({p["store_slug"] for p in g["products"]})) if groups else None

        # From the best group, get cheapest per store
        by_store = {}
        if best_group:
            for p in best_group["products"]:
                slug = p["store_slug"]
                if slug not in by_store or p["current_price"] < by_store[slug]["price"]:
                    by_store[slug] = {
                        "store_name": p["store_name"],
                        "store_slug": slug,
                        "store_color": p["store_color"],
                        "product_name": p["name"],
                        "price": p["current_price"],
                        "unit": p.get("unit"),
                        "image_url": p.get("image_url"),
                        "url": p.get("url"),
                        "subtotal": round(p["current_price"] * item.quantity, 2),
                    }

        best = min(by_store.values(), key=lambda x: x["price"]) if by_store else None

        item_results.append({
            "query": item.search_query,
            "quantity": item.quantity,
            "by_store": by_store,
            "best": best,
        })

    # Calculate per-store totals (if you bought everything at ONE store)
    store_totals = {}
    for item in item_results:
        for slug, data in item["by_store"].items():
            if slug not in store_totals:
                store_totals[slug] = {
                    "store_name": data["store_name"],
                    "store_color": data["store_color"],
                    "total": 0,
                    "items_available": 0,
                    "items_missing": [],
                }
            store_totals[slug]["total"] = round(
                store_totals[slug]["total"] + data["subtotal"], 2
            )
            store_totals[slug]["items_available"] += 1

    # Flag missing items per store
    for item in item_results:
        for slug in store_totals:
            if slug not in item["by_store"]:
                store_totals[slug]["items_missing"].append(item["query"])

    # Best single-store plan
    complete_stores = {
        slug: data for slug, data in store_totals.items()
        if not data["items_missing"]
    }
    best_single_store = (
        min(complete_stores.values(), key=lambda x: x["total"])
        if complete_stores else None
    )

    # Multi-store optimal plan: pick cheapest store per item
    optimal_plan = {}
    optimal_total = 0
    for item in item_results:
        if item["best"]:
            slug = item["best"]["store_slug"]
            if slug not in optimal_plan:
                optimal_plan[slug] = {
                    "store_name": item["best"]["store_name"],
                    "store_color": item["best"]["store_color"],
                    "items": [],
                    "subtotal": 0,
                }
            optimal_plan[slug]["items"].append({
                "query": item["query"],
                "product_name": item["best"]["product_name"],
                "price": item["best"]["price"],
                "quantity": item["quantity"],
                "subtotal": item["best"]["subtotal"],
            })
            optimal_plan[slug]["subtotal"] = round(
                optimal_plan[slug]["subtotal"] + item["best"]["subtotal"], 2
            )
            optimal_total += item["best"]["subtotal"]

    optimal_total = round(optimal_total, 2)

    # Savings vs worst single store
    worst_total = max((v["total"] for v in store_totals.values()), default=0)
    savings_vs_worst = round(worst_total - optimal_total, 2)

    return {
        "list_id": list_id,
        "list_name": sl.name,
        "items": item_results,
        "store_totals": store_totals,
        "best_single_store": best_single_store,
        "optimal_multi_store_plan": {
            "by_store": optimal_plan,
            "total": optimal_total,
            "potential_savings_vs_expensive": savings_vs_worst,
        },
    }
