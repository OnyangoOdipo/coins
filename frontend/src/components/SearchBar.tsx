"use client";
import { useState, useRef } from "react";

const SUGGESTIONS = [
  "Sugar",
  "Unga (Maize Flour)",
  "Cooking Oil",
  "Rice",
  "Milk",
  "Bread",
  "Eggs",
  "Tea Leaves",
  "Tomatoes",
  "Onions",
  "Beef",
  "Chicken",
  "Butter",
  "Yoghurt",
  "Diapers",
];

interface Props {
  onSearch: (query: string, live: boolean) => void;
  loading?: boolean;
  placeholder?: string;
}

export default function SearchBar({ onSearch, loading, placeholder }: Props) {
  const [query, setQuery] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);

  const filtered = SUGGESTIONS.filter((s) =>
    s.toLowerCase().includes(query.toLowerCase())
  ).slice(0, 6);

  function handleSubmit(q: string, live = false) {
    if (!q.trim()) return;
    setShowSuggestions(false);
    onSearch(q.trim(), live);
  }

  return (
    <div className="relative w-full max-w-2xl">
      <div className="flex overflow-hidden rounded-2xl border-2 border-green-500 bg-white shadow-lg focus-within:border-green-600">
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setShowSuggestions(true);
          }}
          onFocus={() => setShowSuggestions(true)}
          onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
          onKeyDown={(e) => e.key === "Enter" && handleSubmit(query)}
          placeholder={placeholder || "Search for sugar, unga, milk..."}
          className="flex-1 bg-transparent px-5 py-4 text-base text-gray-800 outline-none placeholder:text-gray-400"
        />
        <button
          onClick={() => handleSubmit(query, true)}
          disabled={loading || !query.trim()}
          title="Search live (re-scrape stores)"
          className="border-l border-green-200 bg-green-50 px-4 text-green-600 hover:bg-green-100 disabled:opacity-40"
        >
          {loading ? (
            <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
            </svg>
          ) : (
            <span title="Live search (slower, fresher data)">Live</span>
          )}
        </button>
        <button
          onClick={() => handleSubmit(query, false)}
          disabled={loading || !query.trim()}
          className="bg-green-600 px-6 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-40"
        >
          Search
        </button>
      </div>

      {/* Suggestions dropdown */}
      {showSuggestions && query && filtered.length > 0 && (
        <ul className="absolute top-full z-50 mt-1 w-full rounded-xl border border-gray-200 bg-white shadow-xl">
          {filtered.map((s) => (
            <li key={s}>
              <button
                onMouseDown={() => {
                  setQuery(s);
                  handleSubmit(s, false);
                }}
                className="flex w-full items-center gap-3 px-5 py-3 text-sm text-gray-700 hover:bg-green-50 hover:text-green-700"
              >
                <span className="text-gray-400">-</span>
                {s}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
