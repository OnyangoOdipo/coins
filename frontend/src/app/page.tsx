"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import SearchBar from "@/components/SearchBar";
import ProductCard from "@/components/ProductCard";
import { useAuth } from "@/context/AuthContext";
import {
  searchProducts,
  addItemToList,
  createList,
  getMyLists,
} from "@/lib/api";
import { timeAgo } from "@/lib/utils";

interface Product {
  id: number;
  name: string;
  current_price: number | null;
  original_price: number | null;
  unit: string | null;
  image_url: string | null;
  url: string | null;
  last_scraped: string | null;
  store: { name: string; slug: string; color: string };
}

interface SearchResult {
  query: string;
  count: number;
  results: Product[];
}

const CATEGORIES = [
  { label: "Unga / Flour", query: "unga flour" },
  { label: "Cooking Oil", query: "cooking oil" },
  { label: "Dairy / Milk", query: "milk" },
  { label: "Rice", query: "rice" },
  { label: "Bread", query: "bread" },
  { label: "Beef / Chicken", query: "beef" },
  { label: "Toiletries", query: "soap" },
  { label: "Sugar", query: "sugar" },
];

export default function HomePage() {
  const router = useRouter();
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [addedToList, setAddedToList] = useState<Record<number, boolean>>({});
  const [currentQuery, setCurrentQuery] = useState("");

  async function handleSearch(query: string, live: boolean) {
    setLoading(true);
    setError(null);
    setCurrentQuery(query);
    try {
      const data = await searchProducts(query, live);
      setResult(data);
    } catch {
      setError(
        "Could not connect to the API. Make sure the backend is running on port 8000."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleAddToList(productName: string, productId: number) {
    if (!user) {
      router.push("/login");
      return;
    }
    try {
      const lists = await getMyLists();
      let listId: number;
      if (lists.length > 0) {
        listId = lists[0].id;
      } else {
        const newList = await createList("My Shopping List");
        listId = newList.id;
      }
      await addItemToList(listId, { search_query: productName, quantity: 1 });
      setAddedToList((prev) => ({ ...prev, [productId]: true }));
      setTimeout(
        () => setAddedToList((prev) => ({ ...prev, [productId]: false })),
        2000
      );
    } catch (e) {
      console.error("Failed to add to list", e);
    }
  }

  const sorted = result?.results
    .slice()
    .sort(
      (a, b) => (a.current_price ?? Infinity) - (b.current_price ?? Infinity)
    );
  const cheapestId = sorted?.[0]?.id;

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      {/* Hero */}
      <div className="mb-10 text-center">
        <h1 className="mb-3 text-4xl font-black text-gray-900">
          Stop Overpaying for Groceries
        </h1>
        <p className="mb-8 text-lg text-gray-500">
          Compare prices across{" "}
          <span className="font-semibold text-red-600">Naivas</span>,{" "}
          <span className="font-semibold text-blue-700">Carrefour</span> &{" "}
          <span className="font-semibold text-red-500">Quickmart</span> —
          instantly.
        </p>
        <div className="flex justify-center">
          <SearchBar onSearch={handleSearch} loading={loading} />
        </div>
        <p className="mt-3 text-xs text-gray-400">
          Live search scrapes stores now (~15s) | Regular uses cached data
        </p>
      </div>

      {/* Category chips */}
      {!result && !loading && (
        <>
          <div className="mb-8 flex flex-wrap justify-center gap-2">
            {CATEGORIES.map((c) => (
              <button
                key={c.query}
                onClick={() => handleSearch(c.query, false)}
                className="flex items-center gap-1.5 rounded-full border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm transition hover:border-green-400 hover:bg-green-50 hover:text-green-700"
              >
                {c.label}
              </button>
            ))}
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            {[
              {
                title: "Search any item",
                desc: "Type what you need — sugar, milk, unga, diapers, anything.",
              },
              {
                title: "Compare prices",
                desc: "See live prices from Naivas, Carrefour & Quickmart side by side.",
              },
              {
                title: "Save money",
                desc: "Know exactly which store saves you the most before you leave home.",
              },
            ].map((s) => (
              <div
                key={s.title}
                className="rounded-2xl border border-gray-200 bg-white p-6 text-center shadow-sm"
              >
                <h3 className="mb-1 font-bold text-gray-800">{s.title}</h3>
                <p className="text-sm text-gray-500">{s.desc}</p>
              </div>
            ))}
          </div>
        </>
      )}

      {/* Loading */}
      {loading && (
        <div className="py-16 text-center">
          <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-4 border-green-500 border-t-transparent" />
          <p className="text-gray-500">Searching across all stores...</p>
          <p className="mt-1 text-xs text-gray-400">
            Live search may take up to 20 seconds
          </p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-center text-red-700">
          {error}
        </div>
      )}

      {/* Results */}
      {result && !loading && (
        <div>
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-xl font-bold text-gray-800">
                Results for &ldquo;{result.query}&rdquo;
              </h2>
              <p className="text-sm text-gray-500">
                {result.count} products found
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() =>
                  router.push(
                    `/compare?q=${encodeURIComponent(currentQuery)}`
                  )
                }
                className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
              >
                Compare Prices →
              </button>
              <button
                onClick={() => router.push("/list")}
                className="rounded-xl border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                My List
              </button>
            </div>
          </div>

          {result.count === 0 ? (
            <div className="rounded-2xl border border-dashed border-gray-300 py-16 text-center">
              <p className="mt-3 font-medium text-gray-600">
                No products found for &ldquo;{result.query}&rdquo;
              </p>
              <p className="mt-1 text-sm text-gray-400">
                Try a live search to scrape fresh data from stores.
              </p>
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
              {sorted?.map((product) => (
                <div key={product.id} className="relative">
                  {addedToList[product.id] && (
                    <div className="absolute inset-0 z-10 flex items-center justify-center rounded-xl bg-green-500/90 font-bold text-white">
                      Added!
                    </div>
                  )}
                  <ProductCard
                    product={product}
                    isBestDeal={product.id === cheapestId}
                    onAddToList={(name) => handleAddToList(name, product.id)}
                  />
                </div>
              ))}
            </div>
          )}

          {sorted && sorted.length > 0 && (
            <p className="mt-4 text-center text-xs text-gray-400">
              Data last updated: {timeAgo(sorted[0].last_scraped)}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
