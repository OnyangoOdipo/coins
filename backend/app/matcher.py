"""
Groq-powered product matcher.
Groups products from different stores that are genuinely the same item
(same type, brand, size/weight) so price comparisons are apples-to-apples.

Two-step process:
1. Pre-filter: remove products that are clearly not what the user searched for
2. Groq grouping: group remaining products by exact product identity
"""
import json
import os
import re
import httpx
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

MAX_PRODUCTS_FOR_GROQ = 80

# Words that stores add to product names but don't change the product identity.
# "Kabras Packed Sugar White 1Kg" == "Kabras Sugar White 1Kg"
# "Naivas Local Sugar White 1Kg" is a Naivas store brand, "Local" is noise.
NOISE_WORDS = re.compile(
    r'\b(?:packed|local|weighed|loose)\b',
    re.IGNORECASE,
)


def _clean_name_for_matching(name: str) -> str:
    """Strip store-specific noise words for better cross-store matching."""
    cleaned = NOISE_WORDS.sub('', name)
    # Collapse multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def _pre_filter(query: str, products: list[dict]) -> list[dict]:
    """
    Remove products that matched the DB LIKE query but are clearly
    not the product the user is looking for.

    Examples for query "sugar":
      KEEP: "Kabras White Sugar 1kg", "Mumias Sugar 2kg"
      DROP: "Wow Sugared 20G" (candy), "Coffee Sugar Free" (coffee)
      DROP: "Sugar Coated Peanuts" (peanuts, not sugar)
    """
    if not products:
        return products

    q_lower = query.lower().strip()
    q_words = q_lower.split()

    # Build exclusion patterns: word variations that indicate the product
    # is NOT actually the searched item
    # e.g., for "sugar": "sugar-free", "sugar free", "sugared", "sugary"
    exclude_patterns = []
    for word in q_words:
        # "sugar-free", "sugar free"
        exclude_patterns.append(re.compile(
            rf'\b{re.escape(word)}[\s-]*free\b', re.IGNORECASE
        ))
        # "sugared", "sugary" — query word as adjective/modifier
        exclude_patterns.append(re.compile(
            rf'\b{re.escape(word)}(?:ed|y|ing)\b', re.IGNORECASE
        ))

    filtered = []
    for p in products:
        name = p.get("name", "")
        name_lower = name.lower()

        # Check if any exclusion pattern matches
        excluded = False
        for pattern in exclude_patterns:
            if pattern.search(name_lower):
                excluded = True
                break

        if excluded:
            continue

        # Check that the query word appears as a meaningful part of the product
        # (not just embedded in another word like "oily" for "oil")
        has_match = False
        for word in q_words:
            # Allow the word to appear as a standalone word or as a prefix
            # e.g., "sugar" matches "sugar", "sugars" but NOT "sugared"
            word_pattern = re.compile(
                rf'\b{re.escape(word)}s?\b', re.IGNORECASE
            )
            if word_pattern.search(name_lower):
                has_match = True
                break

        if has_match:
            filtered.append(p)

    # If filtering removed everything, return originals (don't break the UX)
    return filtered if filtered else products


def _build_prompt(query: str, products: list[dict]) -> str:
    """Build the prompt that asks the LLM to group equivalent products."""
    product_lines = []
    for i, p in enumerate(products):
        store = p.get("store") or p.get("store_slug", "?")
        # Use cleaned name so Groq sees "Kabras Sugar White 1Kg" not "Kabras Packed Sugar White 1Kg"
        name = _clean_name_for_matching(p.get("name", "?"))
        price = p.get("current_price", "?")
        unit = p.get("unit") or ""
        product_lines.append(f"{i}: [{store}] {name} {unit} - KES {price}")

    product_list = "\n".join(product_lines)

    return f"""You are a Kenyan grocery product matching engine.

The user searched for: "{query}"

Here are products from different stores:
{product_list}

TASK: Group products that are the EXACT SAME item across stores.
"Same item" means: same product type, same brand (if branded), and same or very similar size/weight.

STRICT RULES:
1. "Mumias Sugar White 1Kg" from Naivas and "MUMIAS SUGAR WHITE 1KG" from Carrefour -> SAME, group them
2. "Kabras Sugar White 1Kg" from Quickmart and "Kabras Sugar White 1Kg" from Naivas -> SAME, group them
3. "Sugar 1Kg" and "Sugar 2Kg" -> DIFFERENT sizes, separate groups
4. "Sugar 1Kg" and "Sugared Candy 15g" -> COMPLETELY DIFFERENT products, separate groups
5. "Fresh Milk 500ml" and "Milk Chocolate 100g" -> COMPLETELY DIFFERENT, separate groups
6. Products that are NOT actually "{query}" must be excluded — set relevant=false
7. Ignore case, spacing differences, and minor word order differences when matching
8. Only group products a shopper would consider interchangeable at the shelf
9. A product can only appear in ONE group
10. Use the most descriptive product name as the group label (include brand + size)

IMPORTANT: Only return groups for products that ARE actually "{query}".
Exclude products where "{query}" is just a modifier (e.g., "sugar-free coffee" is coffee, not sugar).

Return ONLY valid JSON:
{{"groups": [{{"label": "Brand Product Size", "items": [0, 2, 5], "relevant": true}}, ...]}}

Where:
- "items" = product index numbers from the list above
- "relevant" = true if this group is actually the product type "{query}", false if it's something else"""


def match_products(query: str, products: list[dict]) -> list[dict]:
    """
    Pre-filter + Groq LLM grouping of equivalent products across stores.

    Returns list of groups:
    [
        {
            "label": "Mumias White Sugar 1kg",
            "products": [<product_dict>, <product_dict>, ...]
        },
        ...
    ]
    """
    if not products:
        return []

    # Step 1: Pre-filter obvious non-matches
    filtered = _pre_filter(query, products)

    # Cap at MAX_PRODUCTS_FOR_GROQ to keep prompt manageable
    if len(filtered) > MAX_PRODUCTS_FOR_GROQ:
        filtered = filtered[:MAX_PRODUCTS_FOR_GROQ]

    if not GROQ_API_KEY:
        return _fallback_group(filtered)

    prompt = _build_prompt(query, filtered)

    try:
        resp = httpx.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 4096,
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )

        if resp.status_code != 200:
            print(f"[Matcher] Groq API error {resp.status_code}: {resp.text[:200]}")
            return _fallback_group(filtered)

        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        result = json.loads(content)
        groups_raw = result.get("groups", [])

        # Build final groups with actual product dicts
        # Only include groups marked as relevant
        groups = []
        used = set()
        for g in groups_raw:
            # Skip groups the LLM marked as not relevant
            if not g.get("relevant", True):
                continue

            indices = g.get("items", [])
            group_products = []
            for idx in indices:
                if isinstance(idx, int) and 0 <= idx < len(filtered) and idx not in used:
                    group_products.append(filtered[idx])
                    used.add(idx)
            if group_products:
                groups.append({
                    "label": g.get("label", group_products[0]["name"]),
                    "products": group_products,
                })

        # Don't add missed products as single-item groups — they're likely
        # irrelevant products that the LLM intentionally excluded

        return groups

    except Exception as e:
        print(f"[Matcher] Error: {e}")
        return _fallback_group(filtered)


def _fallback_group(products: list[dict]) -> list[dict]:
    """Simple fallback: group by exact normalized_name."""
    groups = {}
    for p in products:
        key = p.get("normalized_name", p["name"].lower())
        if key not in groups:
            groups[key] = {"label": p["name"], "products": []}
        groups[key]["products"].append(p)
    return list(groups.values())
