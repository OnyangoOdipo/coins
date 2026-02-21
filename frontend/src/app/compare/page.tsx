"use client";
import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import SearchBar from "@/components/SearchBar";
import { compareProducts } from "@/lib/api";
import { formatKES } from "@/lib/utils";

interface ProductInfo {
  id: number;
  name: string;
  current_price: number | null;
  original_price: number | null;
  unit: string | null;
  image_url: string | null;
  url: string | null;
}

interface StoreEntry {
  store: { name: string; slug: string; color: string };
  product: ProductInfo;
}

interface GroupData {
  label: string;
  image_url: string | null;
  stores: StoreEntry[];
  store_count: number;
  cheapest: { store_slug: string; store_name: string; price: number } | null;
  savings: { amount: number; percentage: number } | null;
}

interface CompareResult {
  query: string;
  groups: GroupData[];
  summary: {
    total_groups: number;
    multi_store_groups: number;
    best_saving: {
      label: string;
      amount: number;
      percentage: number;
      store: string;
    } | null;
  } | null;
}

function CompareContent() {
  const params = useSearchParams();
  const initialQuery = params.get("q") || "";
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CompareResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "multi">("multi");

  async function handleSearch(query: string, live: boolean) {
    setLoading(true);
    setError(null);
    try {
      const data = await compareProducts(query, live);
      setResult(data);
    } catch {
      setError("Failed to compare prices. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (initialQuery) handleSearch(initialQuery, false);
  }, []);

  const displayGroups = (result?.groups ?? []).filter((g) =>
    filter === "multi" ? g.store_count > 1 : true
  );

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <div className="mb-8 text-center">
        <h1 className="mb-2 text-3xl font-black text-gray-900">
          Price Comparison
        </h1>
        <p className="mb-6 text-gray-500">
          Compare the exact same product across stores — item for item.
        </p>
        <div className="flex justify-center">
          <SearchBar onSearch={handleSearch} loading={loading} />
        </div>
      </div>

      {loading && (
        <div className="py-16 text-center">
          <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
          <p className="text-gray-500">Comparing prices across stores...</p>
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-center text-red-700">
          {error}
        </div>
      )}

      {result && !loading && (
        <div>
          {/* Summary banner */}
          {result.summary?.best_saving && (
            <div className="mb-6 rounded-2xl bg-gradient-to-r from-green-500 to-emerald-600 p-5 text-white shadow-lg">
              <p className="text-sm font-medium opacity-80">
                Best saving for &ldquo;{result.query}&rdquo;
              </p>
              <p className="mt-1 text-xl font-black">
                Save{" "}
                <span className="underline decoration-wavy">
                  {formatKES(result.summary.best_saving.amount)}
                </span>{" "}
                ({result.summary.best_saving.percentage}%) on{" "}
                {result.summary.best_saving.label}
              </p>
              <p className="mt-1 text-sm opacity-75">
                by shopping at {result.summary.best_saving.store}
              </p>
            </div>
          )}

          {/* Stats + filter */}
          {result.groups.length > 0 && (
            <div className="mb-4 flex items-center justify-between">
              <p className="text-sm text-gray-500">
                {result.summary?.total_groups || 0} product
                {(result.summary?.total_groups || 0) !== 1 ? "s" : ""} found
                {result.summary?.multi_store_groups
                  ? ` — ${result.summary.multi_store_groups} available at multiple stores`
                  : ""}
              </p>
              <div className="flex gap-1 rounded-lg bg-gray-100 p-0.5">
                <button
                  onClick={() => setFilter("multi")}
                  className={`rounded-md px-3 py-1 text-xs font-medium transition ${
                    filter === "multi"
                      ? "bg-white text-gray-900 shadow-sm"
                      : "text-gray-500 hover:text-gray-700"
                  }`}
                >
                  Multi-store
                </button>
                <button
                  onClick={() => setFilter("all")}
                  className={`rounded-md px-3 py-1 text-xs font-medium transition ${
                    filter === "all"
                      ? "bg-white text-gray-900 shadow-sm"
                      : "text-gray-500 hover:text-gray-700"
                  }`}
                >
                  All
                </button>
              </div>
            </div>
          )}

          {(!displayGroups || displayGroups.length === 0) ? (
            <div className="rounded-2xl border border-dashed border-gray-300 py-16 text-center">
              <p className="text-4xl">🤷</p>
              <p className="mt-3 font-medium text-gray-600">
                {result.groups.length === 0
                  ? `No results for "${result.query}"`
                  : "No multi-store comparisons found"}
              </p>
              <p className="mt-1 text-sm text-gray-400">
                {result.groups.length === 0
                  ? "Try a different search term or use live search."
                  : "Switch to \"All\" to see single-store products too."}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {displayGroups.map((group, gi) => (
                <GroupCard key={gi} group={group} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function GroupCard({ group }: { group: GroupData }) {
  const maxPrice = Math.max(
    ...group.stores.map((s) => s.product.current_price || 0)
  );

  return (
    <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm transition-shadow hover:shadow-md">
      {/* Group header */}
      <div className="flex items-center gap-4 border-b border-gray-100 px-5 py-4">
        {group.image_url && (
          <img
            src={group.image_url}
            alt={group.label}
            className="h-14 w-14 rounded-lg object-contain"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
        )}
        <div className="min-w-0 flex-1">
          <h3 className="font-bold text-gray-900">{group.label}</h3>
          <p className="text-xs text-gray-400">
            Available at {group.store_count} store
            {group.store_count !== 1 ? "s" : ""}
          </p>
        </div>
        {group.savings && (
          <div className="shrink-0 rounded-full bg-green-50 px-3 py-1 text-xs font-bold text-green-700">
            Save {formatKES(group.savings.amount)} ({group.savings.percentage}%)
          </div>
        )}
      </div>

      {/* Store rows */}
      <div className="divide-y divide-gray-50">
        {group.stores.map((entry, si) => {
          const price = entry.product.current_price || 0;
          const pct = maxPrice ? (price / maxPrice) * 100 : 0;
          const isCheapest =
            group.cheapest?.store_slug === entry.store.slug;
          const isMostExpensive =
            group.store_count > 1 && si === group.stores.length - 1;

          return (
            <div
              key={entry.store.slug}
              className={`flex items-center gap-3 px-5 py-3 ${
                isCheapest ? "bg-green-50/50" : ""
              }`}
            >
              {/* Store badge */}
              <div
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[10px] font-bold text-white"
                style={{ backgroundColor: entry.store.color }}
              >
                {entry.store.name.charAt(0)}
              </div>

              {/* Store name + product name */}
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-gray-800">
                    {entry.store.name}
                  </span>
                  {isCheapest && group.store_count > 1 && (
                    <span className="rounded bg-green-500 px-1.5 py-0.5 text-[10px] font-bold text-white">
                      CHEAPEST
                    </span>
                  )}
                  {isMostExpensive && (
                    <span className="rounded bg-orange-400 px-1.5 py-0.5 text-[10px] font-bold text-white">
                      PRICIEST
                    </span>
                  )}
                </div>
                <p className="truncate text-xs text-gray-400">
                  {entry.product.name}
                </p>
                {/* Price bar */}
                <div className="mt-1 h-1.5 w-full rounded-full bg-gray-100">
                  <div
                    className="h-1.5 rounded-full transition-all duration-500"
                    style={{
                      width: `${pct}%`,
                      backgroundColor: entry.store.color,
                      opacity: isCheapest ? 1 : 0.5,
                    }}
                  />
                </div>
              </div>

              {/* Price + link */}
              <div className="shrink-0 text-right">
                <p
                  className={`text-lg font-black ${
                    isCheapest ? "text-green-700" : "text-gray-900"
                  }`}
                >
                  {formatKES(price)}
                </p>
                {entry.product.original_price &&
                  entry.product.original_price !== entry.product.current_price && (
                    <p className="text-xs text-gray-400 line-through">
                      {formatKES(entry.product.original_price)}
                    </p>
                  )}
                {entry.product.url && (
                  <a
                    href={entry.product.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-0.5 inline-block text-[10px] font-medium text-blue-500 hover:underline"
                  >
                    View →
                  </a>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function ComparePage() {
  return (
    <Suspense>
      <CompareContent />
    </Suspense>
  );
}
