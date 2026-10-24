import { useState } from "react";
import { Link } from "react-router-dom";
import type { Product } from "../types/marketplace";

export function ProductCard({ product }: { product: Product }) {
  const [imageError, setImageError] = useState(false);

  return (
    <article className="group flex flex-col">
      <Link aria-label={`View ${product.name}`} to={`/products/${product.id}`} className="block">
        <div className="relative aspect-[4/5] w-full overflow-hidden bg-[#ECE8E1]">
          {imageError || !product.imageUrl ? (
            <div className="flex h-full w-full flex-col items-center justify-center p-4 text-center text-ink/40">
              <svg className="h-8 w-8 stroke-1 text-ink/30 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              <span className="text-xs uppercase tracking-wider font-light text-ink/50">{product.name}</span>
            </div>
          ) : (
            <img
              alt={product.name}
              className="h-full w-full object-cover object-center transition duration-500 ease-out group-hover:scale-[1.03]"
              loading="lazy"
              onError={() => setImageError(true)}
              src={product.imageUrl}
            />
          )}

          {/* Availability badge */}
          {product.availableStock === 0 ? (
            <span className="absolute left-3 top-3 border border-borderIvory bg-paper/95 px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.2em] text-ink/70 backdrop-blur-sm">
              Sold out
            </span>
          ) : null}
        </div>

        {/* Metadata */}
        <div className="mt-3.5 flex flex-col space-y-1">
          <div className="flex items-center justify-between gap-1.5 text-[11px] uppercase tracking-[0.12em] sm:tracking-[0.14em] text-ink/50">
            <span className="truncate">{product.designer}</span>
            <span className="capitalize shrink-0 text-[10px] sm:text-[11px]">{product.category}</span>
          </div>

          <h3 className="font-sans text-sm font-normal text-ink transition-colors group-hover:text-ink/75 line-clamp-1 break-words">
            {product.name}
          </h3>

          <div className="flex items-center justify-between gap-1.5 pt-0.5">
            <span className="font-sans text-sm font-medium text-ink shrink-0">
              ${product.price.toFixed(2)}
            </span>
            {product.color && (
              <span className="text-[11px] text-ink/45 lowercase truncate text-right">
                {product.color}
              </span>
            )}
          </div>
        </div>
      </Link>
    </article>
  );
}
