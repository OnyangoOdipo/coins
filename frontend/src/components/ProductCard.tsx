import { formatKES } from "@/lib/utils";

interface Store {
  name: string;
  slug: string;
  color: string;
}

interface Product {
  id: number;
  name: string;
  current_price: number | null;
  original_price: number | null;
  unit: string | null;
  image_url: string | null;
  url: string | null;
  store: Store;
}

interface Props {
  product: Product;
  isBestDeal?: boolean;
  onAddToList?: (name: string) => void;
}

export default function ProductCard({ product, isBestDeal, onAddToList }: Props) {
  const discount =
    product.original_price && product.current_price
      ? Math.round(
          ((product.original_price - product.current_price) /
            product.original_price) *
            100
        )
      : 0;

  return (
    <div
      className={`relative flex flex-col rounded-xl border bg-white shadow-sm transition-shadow hover:shadow-md ${
        isBestDeal ? "border-green-400 ring-2 ring-green-300" : "border-gray-200"
      }`}
    >
      {isBestDeal && (
        <div className="best-deal-badge absolute -top-3 left-3 rounded-full bg-green-500 px-3 py-0.5 text-xs font-bold text-white shadow">
          Best Deal
        </div>
      )}

      {discount > 0 && (
        <div className="absolute -top-3 right-3 rounded-full bg-red-500 px-2 py-0.5 text-xs font-bold text-white">
          -{discount}%
        </div>
      )}

      {/* Store badge */}
      <div
        className="rounded-t-xl px-3 py-1.5 text-xs font-semibold text-white"
        style={{ backgroundColor: product.store.color }}
      >
        {product.store.name}
      </div>

      <div className="flex flex-1 flex-col p-3">
        {/* Image */}
        {product.image_url ? (
          <div className="mb-2 flex h-28 items-center justify-center overflow-hidden rounded-lg bg-gray-50">
            <img
              src={product.image_url}
              alt={product.name}
              className="max-h-28 max-w-full object-contain"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = "none";
              }}
            />
          </div>
        ) : (
          <div className="mb-2 flex h-28 items-center justify-center rounded-lg bg-gray-50 text-sm text-gray-300">
            No image
          </div>
        )}

        {/* Name */}
        <p className="mb-1 line-clamp-2 flex-1 text-sm font-medium text-gray-800">
          {product.name}
        </p>

        {product.unit && (
          <p className="mb-1 text-xs text-gray-500">{product.unit}</p>
        )}

        {/* Price */}
        <div className="mt-auto">
          <div className="flex items-baseline gap-2">
            <span className="text-lg font-bold text-gray-900">
              {formatKES(product.current_price)}
            </span>
            {product.original_price && product.original_price !== product.current_price && (
              <span className="text-sm text-gray-400 line-through">
                {formatKES(product.original_price)}
              </span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="mt-2 flex gap-2">
          {product.url && (
            <a
              href={product.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 rounded-lg border border-gray-200 py-1.5 text-center text-xs font-medium text-gray-600 hover:bg-gray-50"
            >
              View
            </a>
          )}
          {onAddToList && (
            <button
              onClick={() => onAddToList(product.name)}
              className="flex-1 rounded-lg bg-green-600 py-1.5 text-xs font-medium text-white hover:bg-green-700"
            >
              + List
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
