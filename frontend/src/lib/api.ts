const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("coins_token");
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ---- Public endpoints ----

export async function searchProducts(query: string, live?: boolean) {
  const params = new URLSearchParams({ q: query });
  if (live) params.set("live", "true");
  const res = await fetch(`${API_BASE}/products/search?${params}`);
  if (!res.ok) throw new Error("Search failed");
  return res.json();
}

export async function compareProducts(query: string, live?: boolean) {
  const params = new URLSearchParams({ q: query });
  if (live) params.set("live", "true");
  const res = await fetch(`${API_BASE}/products/compare?${params}`);
  if (!res.ok) throw new Error("Compare failed");
  return res.json();
}

export async function getPriceHistory(productId: number) {
  const res = await fetch(`${API_BASE}/products/${productId}/history`);
  if (!res.ok) throw new Error("Failed to get history");
  return res.json();
}

export async function getStores() {
  const res = await fetch(`${API_BASE}/stores/`);
  if (!res.ok) throw new Error("Failed to get stores");
  return res.json();
}

export async function getStoreStats() {
  const res = await fetch(`${API_BASE}/stores/stats`);
  if (!res.ok) throw new Error("Failed to get stats");
  return res.json();
}

// ---- Protected shopping list endpoints ----

export async function createList(name: string) {
  const res = await fetch(`${API_BASE}/lists/`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error("Failed to create list");
  return res.json();
}

export async function getMyLists() {
  const res = await fetch(`${API_BASE}/lists/`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to get lists");
  return res.json();
}

export async function getList(listId: number) {
  const res = await fetch(`${API_BASE}/lists/${listId}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to get list");
  return res.json();
}

export async function addItemToList(
  listId: number,
  item: { search_query: string; quantity: number; notes?: string }
) {
  const res = await fetch(`${API_BASE}/lists/${listId}/items`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(item),
  });
  if (!res.ok) throw new Error("Failed to add item");
  return res.json();
}

export async function removeItemFromList(listId: number, itemId: number) {
  const res = await fetch(`${API_BASE}/lists/${listId}/items/${itemId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to remove item");
  return res.json();
}

export async function optimizeList(listId: number) {
  const res = await fetch(`${API_BASE}/lists/${listId}/optimize`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to optimize list");
  return res.json();
}
