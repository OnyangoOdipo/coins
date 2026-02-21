"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  getList,
  createList,
  addItemToList,
  removeItemFromList,
  optimizeList,
  getMyLists,
} from "@/lib/api";
import { formatKES } from "@/lib/utils";

interface ListItem {
  id: number;
  search_query: string;
  quantity: number;
  notes?: string;
}

interface OptimizeResult {
  list_name: string;
  items: Array<{
    query: string;
    quantity: number;
    by_store: Record<
      string,
      {
        store_name: string;
        store_slug: string;
        store_color: string;
        product_name: string;
        price: number;
        unit: string | null;
        subtotal: number;
      }
    >;
    best: {
      store_name: string;
      store_color: string;
      price: number;
      subtotal: number;
    } | null;
  }>;
  store_totals: Record<
    string,
    {
      store_name: string;
      store_color: string;
      total: number;
      items_available: number;
      items_missing: string[];
    }
  >;
  best_single_store: {
    store_name: string;
    total: number;
    store_color: string;
  } | null;
  optimal_multi_store_plan: {
    by_store: Record<
      string,
      {
        store_name: string;
        store_color: string;
        items: Array<{
          query: string;
          product_name: string;
          price: number;
          quantity: number;
          subtotal: number;
        }>;
        subtotal: number;
      }
    >;
    total: number;
    potential_savings_vs_expensive: number;
  };
}

export default function ListPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [listId, setListIdState] = useState<number | null>(null);
  const [items, setItems] = useState<ListItem[]>([]);
  const [newItem, setNewItem] = useState("");
  const [qty, setQty] = useState(1);
  const [loading, setLoading] = useState(false);
  const [optimizing, setOptimizing] = useState(false);
  const [optimization, setOptimization] = useState<OptimizeResult | null>(null);
  const [activeTab, setActiveTab] = useState<"list" | "plan">("list");

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login");
    }
  }, [authLoading, user, router]);

  useEffect(() => {
    if (user) initList();
  }, [user]);

  async function initList() {
    try {
      const lists = await getMyLists();
      let id: number;
      if (lists.length > 0) {
        id = lists[0].id;
      } else {
        const newList = await createList("My Shopping List");
        id = newList.id;
      }
      setListIdState(id);
      const data = await getList(id);
      setItems(data.items);
    } catch (e) {
      console.error("Failed to init list", e);
    }
  }

  // Auth loading state
  if (authLoading) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-10">
        <div className="mb-4 h-8 w-48 animate-pulse rounded bg-gray-200" />
        <div className="h-12 w-full animate-pulse rounded-xl bg-gray-200" />
      </div>
    );
  }

  // Not logged in — redirect handled by useEffect
  if (!user) return null;

  async function handleAdd() {
    if (!newItem.trim() || !listId) return;
    setLoading(true);
    try {
      await addItemToList(listId, { search_query: newItem.trim(), quantity: qty });
      const data = await getList(listId);
      setItems(data.items);
      setNewItem("");
      setQty(1);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function handleRemove(itemId: number) {
    if (!listId) return;
    await removeItemFromList(listId, itemId);
    setItems((prev) => prev.filter((i) => i.id !== itemId));
    setOptimization(null);
  }

  async function handleOptimize() {
    if (!listId || items.length === 0) return;
    setOptimizing(true);
    setActiveTab("plan");
    try {
      const data = await optimizeList(listId);
      setOptimization(data);
    } catch (e) {
      console.error(e);
    } finally {
      setOptimizing(false);
    }
  }

  const storeTotalsArr = optimization
    ? Object.entries(optimization.store_totals).sort(
        ([, a], [, b]) => a.total - b.total
      )
    : [];

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <div className="mb-6">
        <h1 className="text-3xl font-black text-gray-900">My Shopping List</h1>
        <p className="text-gray-500">
          Add items and we&apos;ll tell you exactly where to shop to save the most.
        </p>
      </div>

      {/* Add item */}
      <div className="mb-6 flex gap-2">
        <input
          type="text"
          value={newItem}
          onChange={(e) => setNewItem(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAdd()}
          placeholder="Add item, e.g. Sugar 1kg, Kabras Sugar 1kg..."
          className="flex-1 rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm shadow-sm outline-none focus:border-green-500 focus:ring-2 focus:ring-green-200"
        />
        <input
          type="number"
          value={qty}
          min={1}
          onChange={(e) => setQty(Math.max(1, parseInt(e.target.value) || 1))}
          className="w-16 rounded-xl border border-gray-200 bg-white px-3 py-3 text-center text-sm shadow-sm outline-none focus:border-green-500"
        />
        <button
          onClick={handleAdd}
          disabled={loading || !newItem.trim()}
          className="rounded-xl bg-green-600 px-5 py-3 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-40"
        >
          {loading ? "..." : "+ Add"}
        </button>
      </div>

      {/* Tabs */}
      <div className="mb-4 flex gap-2 border-b border-gray-200">
        {(["list", "plan"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-semibold capitalize transition-colors ${
              activeTab === tab
                ? "border-b-2 border-green-600 text-green-600"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab === "list" ? `Items (${items.length})` : "Savings Plan"}
          </button>
        ))}
      </div>

      {/* List tab */}
      {activeTab === "list" && (
        <div>
          {items.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-gray-300 py-16 text-center">
              <p className="mt-3 font-medium text-gray-600">
                Your list is empty
              </p>
              <p className="mt-1 text-sm text-gray-400">
                Add items above to get started
              </p>
            </div>
          ) : (
            <>
              <ul className="space-y-2">
                {items.map((item) => (
                  <li
                    key={item.id}
                    className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3 shadow-sm"
                  >
                    <span className="flex-1 text-sm font-medium text-gray-800">
                      {item.search_query}
                    </span>
                    <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                      x{item.quantity}
                    </span>
                    <button
                      onClick={() => handleRemove(item.id)}
                      className="text-gray-300 hover:text-red-500"
                    >
                      x
                    </button>
                  </li>
                ))}
              </ul>

              <div className="mt-6">
                <button
                  onClick={() => handleOptimize()}
                  disabled={optimizing}
                  className="w-full rounded-xl bg-green-600 py-3 font-semibold text-white hover:bg-green-700 disabled:opacity-50"
                >
                  {optimizing ? "Calculating..." : "Find Best Deals"}
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* Plan tab */}
      {activeTab === "plan" && (
        <div>
          {optimizing && (
            <div className="py-16 text-center">
              <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-4 border-green-500 border-t-transparent" />
              <p className="text-gray-500">Calculating the best shopping plan...</p>
            </div>
          )}

          {!optimizing && !optimization && (
            <div className="rounded-2xl border border-dashed border-gray-300 py-16 text-center">
              <p className="mt-3 font-medium text-gray-600">
                Go to the Items tab and click &ldquo;Find Best Deals&rdquo;
              </p>
            </div>
          )}

          {optimization && !optimizing && (
            <div className="space-y-6">
              {/* Summary cards */}
              <div className="grid gap-4 md:grid-cols-2">
                {/* Optimal multi-store */}
                <div className="rounded-2xl border-2 border-green-400 bg-green-50 p-5 shadow-sm">
                  <p className="text-xs font-semibold uppercase tracking-wide text-green-700">
                    Optimal Plan (Multi-store)
                  </p>
                  <p className="mt-1 text-3xl font-black text-green-800">
                    {formatKES(optimization.optimal_multi_store_plan.total)}
                  </p>
                  <p className="mt-1 text-sm text-green-700">
                    Buy each item at its cheapest store
                  </p>
                  {optimization.optimal_multi_store_plan
                    .potential_savings_vs_expensive > 0 && (
                    <p className="mt-2 text-sm font-semibold text-green-700">
                      Save{" "}
                      {formatKES(
                        optimization.optimal_multi_store_plan
                          .potential_savings_vs_expensive
                      )}{" "}
                      vs. priciest store
                    </p>
                  )}
                </div>

                {/* Best single store */}
                {optimization.best_single_store && (
                  <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
                    <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">
                      Best Single Store
                    </p>
                    <p
                      className="mt-1 text-3xl font-black"
                      style={{
                        color: optimization.best_single_store.store_color,
                      }}
                    >
                      {formatKES(optimization.best_single_store.total)}
                    </p>
                    <p className="mt-1 text-sm text-gray-600">
                      Shop everything at{" "}
                      <strong>
                        {optimization.best_single_store.store_name}
                      </strong>
                    </p>
                  </div>
                )}
              </div>

              {/* Store totals */}
              <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
                <h3 className="mb-4 font-bold text-gray-800">
                  Single-Store Totals
                </h3>
                <div className="space-y-3">
                  {storeTotalsArr.map(([slug, data], i) => {
                    const maxTotal = storeTotalsArr[storeTotalsArr.length - 1][1].total;
                    const pct = maxTotal ? (data.total / maxTotal) * 100 : 0;
                    return (
                      <div key={slug}>
                        <div className="mb-1 flex items-center justify-between">
                          <span className="text-sm font-medium text-gray-700">
                            {data.store_name}
                            {i === 0 && (
                              <span className="ml-2 rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700">
                                Cheapest
                              </span>
                            )}
                          </span>
                          <span className="text-sm font-bold text-gray-900">
                            {formatKES(data.total)}
                          </span>
                        </div>
                        <div className="h-3 w-full rounded-full bg-gray-100">
                          <div
                            className="h-3 rounded-full transition-all duration-500"
                            style={{
                              width: `${pct}%`,
                              backgroundColor: data.store_color,
                            }}
                          />
                        </div>
                        {data.items_missing.length > 0 && (
                          <p className="mt-0.5 text-xs text-orange-500">
                            Missing: {data.items_missing.join(", ")}
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Per-item breakdown */}
              <div className="rounded-2xl border border-gray-200 bg-white shadow-sm">
                <h3 className="border-b border-gray-100 px-5 py-4 font-bold text-gray-800">
                  Item-by-Item Breakdown
                </h3>
                <div className="divide-y divide-gray-100">
                  {optimization.items.map((item) => (
                    <div key={item.query} className="px-5 py-4">
                      <div className="mb-2 flex items-center justify-between">
                        <p className="font-medium text-gray-800 capitalize">
                          {item.query} ×{item.quantity}
                        </p>
                        {item.best && (
                          <span
                            className="rounded-full px-3 py-0.5 text-xs font-semibold text-white"
                            style={{ backgroundColor: item.best.store_color }}
                          >
                            Buy at: {item.best.store_name}{" "}
                            {formatKES(item.best.subtotal)}
                          </span>
                        )}
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(item.by_store)
                          .sort(([, a], [, b]) => a.price - b.price)
                          .map(([slug, store]) => (
                            <div
                              key={slug}
                              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs ${
                                store.store_slug === item.best?.store_name?.toLowerCase()
                                  ? "bg-green-100 text-green-800 font-semibold"
                                  : "bg-gray-50 text-gray-600"
                              }`}
                            >
                              <span
                                className="h-2 w-2 rounded-full"
                                style={{ backgroundColor: store.store_color }}
                              />
                              {store.store_name}: {formatKES(store.price)}
                            </div>
                          ))}
                        {Object.keys(item.by_store).length === 0 && (
                          <span className="text-xs text-gray-400">
                            Not found in any store
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Optimal plan detail */}
              <div className="rounded-2xl border-2 border-green-300 bg-white shadow-sm">
                <h3 className="border-b border-green-100 bg-green-50 px-5 py-4 font-bold text-green-800 rounded-t-2xl">
                  Your Optimal Shopping Plan
                </h3>
                <div className="divide-y divide-gray-100">
                  {Object.entries(
                    optimization.optimal_multi_store_plan.by_store
                  ).map(([slug, storeData]) => (
                    <div key={slug} className="px-5 py-4">
                      <div className="mb-3 flex items-center gap-2">
                        <span
                          className="h-3 w-3 rounded-full"
                          style={{ backgroundColor: storeData.store_color }}
                        />
                        <h4 className="font-semibold text-gray-800">
                          {storeData.store_name}
                        </h4>
                        <span className="ml-auto font-bold text-gray-900">
                          {formatKES(storeData.subtotal)}
                        </span>
                      </div>
                      <ul className="space-y-1">
                        {storeData.items.map((item) => (
                          <li
                            key={item.query}
                            className="flex items-center justify-between rounded-lg bg-gray-50 px-3 py-2 text-sm"
                          >
                            <span className="text-gray-700">
                              {item.product_name} ×{item.quantity}
                            </span>
                            <span className="font-semibold text-gray-900">
                              {formatKES(item.subtotal)}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
                <div className="flex items-center justify-between rounded-b-2xl bg-green-50 px-5 py-4">
                  <span className="font-bold text-green-800">Grand Total</span>
                  <span className="text-xl font-black text-green-800">
                    {formatKES(optimization.optimal_multi_store_plan.total)}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
