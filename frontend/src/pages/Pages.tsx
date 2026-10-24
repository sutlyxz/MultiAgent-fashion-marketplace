import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { EmptyState, ErrorMessage, Loading } from "../components/Feedback";
import { ProductCard } from "../components/ProductCard";
import { useMarketplace } from "../features/marketplace/MarketplaceContext";
import {
  mockMarketplaceService,
  mockProducts,
  totalFor,
} from "../services/mockMarketplaceService";
import { productService } from "../services/productService";
import { orderService } from "../services/orderService";
import { authService } from "../services/authService";
import {
  MARKETPLACE_CATEGORIES,
  type Order,
  type OrderItem,
  type Product,
  type ProductCreateInput,
  type ProductFilter,
  type ProductUpdateInput,
  type StockItemInput,
  type UserRole,
} from "../types/marketplace";

const money = (amount: number) => `$${amount.toFixed(2)}`;

export function HomePage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  useEffect(() => {
    productService
      .listProducts()
      .then(setProducts)
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Could not load products.");
      })
      .finally(() => setLoading(false));
  }, []);

  const categories = Array.from(
    new Set([...MARKETPLACE_CATEGORIES, ...products.map((p) => p.category).filter(Boolean)]),
  );

  const displayedProducts = selectedCategory
    ? products
      .filter((p) => p.category.toLowerCase() === selectedCategory.toLowerCase())
      .slice(0, 4)
    : products.slice(0, 4);

  return (
    <div className="w-full">
      {/* Editorial Fashion Hero Banner */}
      <section className="relative w-full overflow-hidden bg-[#ECE8E1] min-h-[440px] md:h-[480px] flex items-center">
        {/* Hero Background Image */}
        <img
          src="/clothify-mens-streetwear-hero.png"
          alt="Clothify Editorial Campaign"
          className="absolute inset-0 h-full w-full object-cover object-[80%_center] md:object-[78%_center]"
        />

        {/* Soft gradient overlay for text readability on left side */}
        <div className="absolute inset-0 bg-gradient-to-r from-[#F6F3ED]/95 via-[#F6F3ED]/60 to-transparent md:from-[#F6F3ED]/85 md:via-[#F6F3ED]/25 md:to-transparent" />

        {/* Hero Content */}
        <div className="relative z-10 mx-auto w-full max-w-7xl px-5 sm:px-8 py-16 md:py-0">
          <div className="max-w-xl">
            <p className="eyebrow tracking-[0.25em] text-ink/70">THE CLOTHIFY EDIT</p>
            <h1 className="mt-4 font-display text-4xl sm:text-5xl lg:text-6xl font-normal leading-[1.08] text-ink tracking-tight">
              Timeless Style.<br />
              Modern Essentials.
            </h1>
            <p className="mt-4 max-w-md font-sans text-sm sm:text-base leading-relaxed text-ink/75">
              Discover considered fashion for your everyday wardrobe.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3.5">
              <Link className="button-primary text-center w-full sm:w-auto" to="/products">
                EXPLORE COLLECTION
              </Link>
              <Link className="button-secondary bg-[#F6F3ED]/70 backdrop-blur-sm text-center w-full sm:w-auto" to="/products">
                SHOP ALL
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Category & Product Collection Section */}
      <section className="mx-auto max-w-7xl px-5 sm:px-8 py-14 md:py-20">
        <div className="grid grid-cols-1 md:grid-cols-[18%_1fr] lg:grid-cols-[17%_1fr] gap-8 lg:gap-12 items-start">
          {/* Category Sidebar */}
          <aside className="space-y-6">
            <div>
              <h2 className="font-display text-2xl text-ink font-normal tracking-tight">
                Shop by Category
              </h2>
              <div className="mt-1 h-px w-8 bg-ink/20" />
            </div>

            {/* Desktop Category List */}
            <ul className="hidden md:flex flex-col space-y-3.5 text-xs uppercase tracking-[0.16em] text-ink/70">
              <li>
                <button
                  type="button"
                  onClick={() => setSelectedCategory(null)}
                  className={`text-left transition hover:text-ink ${selectedCategory === null
                    ? "font-semibold text-ink underline underline-offset-4"
                    : ""
                    }`}
                >
                  All Pieces
                </button>
              </li>
              {categories.map((cat) => (
                <li key={cat}>
                  <button
                    type="button"
                    onClick={() => setSelectedCategory(cat)}
                    className={`text-left transition hover:text-ink ${selectedCategory === cat
                      ? "font-semibold text-ink underline underline-offset-4"
                      : ""
                      }`}
                  >
                    {cat}
                  </button>
                </li>
              ))}
            </ul>

            {/* Mobile Category Horizontal Scroll */}
            <div className="flex md:hidden items-center gap-3 overflow-x-auto no-scrollbar pb-2 border-b border-borderIvory/70 text-xs uppercase tracking-wider">
              <button
                type="button"
                onClick={() => setSelectedCategory(null)}
                className={`shrink-0 py-1 ${selectedCategory === null
                  ? "font-semibold text-ink underline underline-offset-4"
                  : "text-ink/60"
                  }`}
              >
                All
              </button>
              {categories.map((cat) => (
                <button
                  key={cat}
                  type="button"
                  onClick={() => setSelectedCategory(cat)}
                  className={`shrink-0 py-1 ${selectedCategory === cat
                    ? "font-semibold text-ink underline underline-offset-4"
                    : "text-ink/60"
                    }`}
                >
                  {cat}
                </button>
              ))}
            </div>

            <div className="pt-2 md:pt-4">
              <Link
                to="/products"
                className="text-xs uppercase tracking-[0.18em] font-medium underline underline-offset-4 text-ink hover:text-ink/70 transition"
              >
                VIEW ALL
              </Link>
            </div>
          </aside>

          {/* Product Grid */}
          <div>
            {error ? (
              <ErrorMessage>{error}</ErrorMessage>
            ) : loading ? (
              <Loading />
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-x-3.5 sm:gap-x-5 gap-y-8 sm:gap-y-10">
                {displayedProducts.map((product) => (
                  <ProductCard key={product.id} product={product} />
                ))}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Verified Benefits Strip */}
      <section className="w-full border-t border-borderIvory bg-[#F2EFE8] py-12 px-5 sm:px-8">
        <div className="mx-auto max-w-7xl grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
          <div className="flex items-start gap-4">
            <svg className="h-6 w-6 shrink-0 text-ink/70 stroke-[1.25]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
            </svg>
            <div>
              <h3 className="font-sans text-xs uppercase tracking-[0.14em] font-semibold text-ink">
                Considered Design
              </h3>
              <p className="mt-1 text-xs text-ink/65 leading-relaxed">
                Thoughtfully curated everyday essentials crafted to endure.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-4">
            <svg className="h-6 w-6 shrink-0 text-ink/70 stroke-[1.25]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
            <div>
              <h3 className="font-sans text-xs uppercase tracking-[0.14em] font-semibold text-ink">
                Curated Makers
              </h3>
              <p className="mt-1 text-xs text-ink/65 leading-relaxed">
                Direct pieces from independent studios and recognized artisans.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-4">
            <svg className="h-6 w-6 shrink-0 text-ink/70 stroke-[1.25]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <h3 className="font-sans text-xs uppercase tracking-[0.14em] font-semibold text-ink">
                Live Inventory
              </h3>
              <p className="mt-1 text-xs text-ink/65 leading-relaxed">
                Transparent, real-time availability across every catalog piece.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-4">
            <svg className="h-6 w-6 shrink-0 text-ink/70 stroke-[1.25]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
            </svg>
            <div>
              <h3 className="font-sans text-xs uppercase tracking-[0.14em] font-semibold text-ink">
                Account Orders
              </h3>
              <p className="mt-1 text-xs text-ink/65 leading-relaxed">
                Seamless order history and session tracking in your profile.
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

export function ProductsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get("q") ?? searchParams.get("search") ?? "";
  const categoryParam = searchParams.get("category") ?? "";
  const colorParam = searchParams.get("color") ?? "";
  const sortBy = searchParams.get("sort_by") ?? "";
  const sortOrder = searchParams.get("sort_order") ?? "";

  const [input, setInput] = useState(query);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const standardCategories = MARKETPLACE_CATEGORIES;

  useEffect(() => {
    setInput(query);
  }, [query]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");

    const filter: ProductFilter = {
      search: query || undefined,
      category: categoryParam || undefined,
      color: colorParam || undefined,
      sortBy: sortBy || undefined,
      sortOrder: sortOrder || undefined,
    };

    productService
      .listProducts(filter)
      .then((result) => {
        if (active) {
          setProducts(result);
        }
      })
      .catch((reason: unknown) => {
        if (active) {
          setProducts([]);
          setError(
            reason instanceof Error
              ? reason.message
              : "Could not load products from server.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [query, categoryParam, colorParam, sortBy, sortOrder]);

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextParams = new URLSearchParams(searchParams);
    if (input.trim()) {
      nextParams.set("q", input.trim());
    } else {
      nextParams.delete("q");
      nextParams.delete("search");
    }
    setSearchParams(nextParams);
  }

  function handleCategoryFilter(cat: string | null) {
    const nextParams = new URLSearchParams(searchParams);
    if (cat) {
      nextParams.set("category", cat);
    } else {
      nextParams.delete("category");
    }
    setSearchParams(nextParams);
  }

  function handleColorFilter(colorVal: string | null) {
    const nextParams = new URLSearchParams(searchParams);
    if (colorVal) {
      nextParams.set("color", colorVal);
    } else {
      nextParams.delete("color");
    }
    setSearchParams(nextParams);
  }

  function handleSortChange(value: string) {
    const nextParams = new URLSearchParams(searchParams);
    if (value === "price_asc") {
      nextParams.set("sort_by", "price");
      nextParams.set("sort_order", "asc");
    } else if (value === "price_desc") {
      nextParams.set("sort_by", "price");
      nextParams.set("sort_order", "desc");
    } else {
      nextParams.delete("sort_by");
      nextParams.delete("sort_order");
    }
    setSearchParams(nextParams);
  }

  function clearFilters() {
    setInput("");
    setSearchParams({});
  }

  const currentSort = sortBy === "price" && sortOrder ? `price_${sortOrder}` : "default";

  // Derive all available categories and colors from known list and current products
  const allCategories = Array.from(
    new Set([...standardCategories, ...products.map((p) => p.category).filter(Boolean)]),
  );

  const availableColors = Array.from(
    new Set(products.map((p) => p.color).filter((c): c is string => Boolean(c))),
  );

  const hasActiveFilters = Boolean(query || categoryParam || colorParam || currentSort !== "default");

  return (
    <section className="mx-auto max-w-7xl px-5 sm:px-8 py-8 md:py-12 space-y-8">
      {/* Editorial Catalog Header */}
      <div className="border-b border-borderIvory pb-8">
        <p className="eyebrow">Clothify · Curated Catalogue</p>
        <div className="mt-3 flex flex-wrap items-baseline justify-between gap-4">
          <h1 className="font-display text-3xl sm:text-4xl md:text-5xl font-normal text-ink tracking-tight flex flex-wrap items-baseline gap-2 sm:gap-3">
            All Pieces
            <span className="font-sans text-xs sm:text-sm font-normal text-ink/40 tracking-wider">
              {products.length} {products.length === 1 ? "piece" : "pieces"}
            </span>
          </h1>
        </div>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-ink/70">
          Considered silhouettes, tactile materials, and enduring design curated for modern everyday living.
        </p>

        {/* Category Filter Pills */}
        <div className="mt-6 flex flex-wrap items-center gap-2 pt-2">
          <button
            type="button"
            onClick={() => handleCategoryFilter(null)}
            className={`rounded-full px-4 py-1.5 text-xs font-medium transition duration-200 ${!categoryParam
              ? "bg-ink text-[#F6F3ED]"
              : "border border-borderIvory bg-paper text-ink/80 hover:border-ink hover:text-ink"
              }`}
          >
            All
          </button>
          {allCategories.map((cat) => {
            const isSelected = categoryParam.toLowerCase() === cat.toLowerCase();
            return (
              <button
                key={cat}
                type="button"
                onClick={() => handleCategoryFilter(isSelected ? null : cat)}
                className={`rounded-full px-4 py-1.5 text-xs font-medium transition duration-200 ${isSelected
                  ? "bg-ink text-[#F6F3ED]"
                  : "border border-borderIvory bg-paper text-ink/80 hover:border-ink hover:text-ink"
                  }`}
              >
                {cat}
              </button>
            );
          })}
        </div>
      </div>

      {/* Filter and Sort Controls */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-borderIvory pb-6">
        <form className="flex flex-1 w-full sm:max-w-md gap-2" onSubmit={submitSearch} role="search">
          <label className="sr-only" htmlFor="product-search">
            Search pieces
          </label>
          <div className="relative flex-1">
            <input
              id="product-search"
              className="field w-full pl-9 pr-4 py-2.5 bg-paper border border-borderIvory text-ink text-xs outline-none transition focus:border-ink focus:ring-1 focus:ring-ink placeholder:text-ink/40"
              onChange={(event) => setInput(event.target.value)}
              placeholder="Search pieces, styles, descriptions..."
              value={input}
            />
            <svg
              className="absolute left-3 top-3 h-3.5 w-3.5 text-ink/40"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.75" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <button className="button-primary py-2.5 px-4 sm:px-5 text-xs shrink-0" type="submit">
            Search
          </button>
        </form>

        <div className="flex flex-wrap items-center gap-3">
          {/* Optional Color Filter */}
          {availableColors.length > 0 && (
            <div className="flex items-center gap-2">
              <label htmlFor="color-filter" className="whitespace-nowrap text-xs uppercase tracking-[0.14em] text-ink/65">
                Color:
              </label>
              <select
                id="color-filter"
                aria-label="Filter by color"
                className="border border-borderIvory bg-paper px-3 py-2 text-xs font-medium uppercase tracking-wider text-ink outline-none transition cursor-pointer hover:border-ink focus:border-ink"
                onChange={(e) => handleColorFilter(e.target.value || null)}
                value={colorParam}
              >
                <option value="">All Colors</option>
                {availableColors.map((color) => (
                  <option key={color} value={color}>
                    {color}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="flex items-center gap-2">
            <label htmlFor="price-sort" className="whitespace-nowrap text-xs uppercase tracking-[0.14em] text-ink/65">
              Sort by:
            </label>
            <select
              id="price-sort"
              aria-label="Sort products by price"
              className="border border-borderIvory bg-paper px-3.5 py-2 text-xs font-medium uppercase tracking-wider text-ink outline-none transition cursor-pointer hover:border-ink focus:border-ink"
              onChange={(e) => handleSortChange(e.target.value)}
              value={currentSort}
            >
              <option value="default">Featured / Default</option>
              <option value="price_asc">Price: Low to High</option>
              <option value="price_desc">Price: High to Low</option>
            </select>
          </div>
        </div>
      </div>

      {/* Active Filter Indicators */}
      {hasActiveFilters && (
        <div className="flex flex-wrap items-center gap-2.5 text-xs text-ink/70">
          <span className="font-semibold uppercase tracking-wider text-ink/60">Active:</span>
          {query && (
            <span className="inline-flex items-center gap-1.5 border border-borderIvory bg-paper px-3 py-1 font-medium text-ink">
              Search: "{query}"
              <button
                type="button"
                onClick={() => {
                  const nextParams = new URLSearchParams(searchParams);
                  nextParams.delete("q");
                  nextParams.delete("search");
                  setInput("");
                  setSearchParams(nextParams);
                }}
                className="ml-1 text-ink/40 hover:text-ink"
                aria-label="Remove search filter"
              >
                ×
              </button>
            </span>
          )}
          {categoryParam && (
            <span className="inline-flex items-center gap-1.5 border border-borderIvory bg-paper px-3 py-1 font-medium text-ink">
              Category: {categoryParam}
              <button
                type="button"
                onClick={() => handleCategoryFilter(null)}
                className="ml-1 text-ink/40 hover:text-ink"
                aria-label="Remove category filter"
              >
                ×
              </button>
            </span>
          )}
          {colorParam && (
            <span className="inline-flex items-center gap-1.5 border border-borderIvory bg-paper px-3 py-1 font-medium text-ink">
              Color: {colorParam}
              <button
                type="button"
                onClick={() => handleColorFilter(null)}
                className="ml-1 text-ink/40 hover:text-ink"
                aria-label="Remove color filter"
              >
                ×
              </button>
            </span>
          )}
          {currentSort === "price_asc" && (
            <span className="inline-flex items-center gap-1.5 border border-borderIvory bg-paper px-3 py-1 font-medium text-ink">
              Price: Low to High
            </span>
          )}
          {currentSort === "price_desc" && (
            <span className="inline-flex items-center gap-1.5 border border-borderIvory bg-paper px-3 py-1 font-medium text-ink">
              Price: High to Low
            </span>
          )}
          <button
            type="button"
            onClick={clearFilters}
            className="sm:ml-auto text-xs font-medium uppercase tracking-wider underline underline-offset-2 hover:text-ink shrink-0"
          >
            Clear all
          </button>
        </div>
      )}

      {/* Catalog Display Grid & States */}
      <div className="pt-2">
        {error ? (
          <div className="py-12">
            <ErrorMessage>{error}</ErrorMessage>
            <div className="mt-4 text-center">
              <button
                type="button"
                onClick={() => {
                  setError("");
                  clearFilters();
                }}
                className="button-primary text-xs"
              >
                Retry loading catalogue
              </button>
            </div>
          </div>
        ) : loading ? (
          <Loading label="Curating the collection…" />
        ) : products.length > 0 ? (
          <div className="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-x-3.5 sm:gap-x-5 gap-y-8 sm:gap-y-12">
            {products.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        ) : hasActiveFilters ? (
          /* Search / Filter Empty State */
          <div className="py-20 text-center border border-borderIvory bg-paper/60">
            <p className="eyebrow">Catalogue Notice</p>
            <h2 className="mt-3 font-display text-3xl text-ink">No matching pieces found</h2>
            <p className="mt-3 text-sm text-ink/60 max-w-md mx-auto">
              We couldn't find anything matching your selected criteria. Try adjusting your search term, category, or clear filters.
            </p>
            <button className="button-primary mt-8" onClick={clearFilters} type="button">
              View full collection
            </button>
          </div>
        ) : (
          /* Catalog Completely Empty State */
          <div className="py-20 text-center border border-borderIvory bg-paper/60">
            <p className="eyebrow">Catalogue Notice</p>
            <h2 className="mt-3 font-display text-3xl text-ink">No pieces currently in catalogue</h2>
            <p className="mt-3 text-sm text-ink/60 max-w-md mx-auto">
              Check back soon for upcoming releases and seasonal curations.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}

export function ProductDetailPage() {
  const { productId = "" } = useParams();
  const { addToCart, user } = useMarketplace();
  const [product, setProduct] = useState<Product | null>(null);
  const [selectedVariantKey, setSelectedVariantKey] = useState<string | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [imageError, setImageError] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    setImageError(false);

    productService
      .getProduct(productId)
      .then((item) => {
        if (active) {
          setProduct(item);
          if (item && item.variants && item.variants.length > 0) {
            // Default to first variant with available quantity, or first variant
            const firstAvailable = item.variants.find((v) => v.availableQuantity > 0);
            setSelectedVariantKey(
              firstAvailable ? firstAvailable.variantKey : item.variants[0].variantKey,
            );
          } else {
            setSelectedVariantKey(null);
          }
        }
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(
            reason instanceof Error ? reason.message : "Could not load product details.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [productId]);

  if (loading) {
    return (
      <div className="mx-auto max-w-7xl px-5 sm:px-8 py-16">
        <Loading label="Loading piece details..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-7xl px-5 sm:px-8 py-16 space-y-4">
        <div>
          <Link
            to="/products"
            className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.14em] font-medium text-ink/60 hover:text-ink transition"
          >
            ← Back to catalogue
          </Link>
        </div>
        <ErrorMessage>{error}</ErrorMessage>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="mx-auto max-w-7xl px-5 sm:px-8 py-16 space-y-4">
        <div>
          <Link
            to="/products"
            className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.14em] font-medium text-ink/60 hover:text-ink transition"
          >
            ← Back to catalogue
          </Link>
        </div>
        <EmptyState
          title="We couldn't find that piece."
          detail="It may have moved on to a new home or is no longer listed in our collection."
          action="Return to Catalog"
          to="/products"
        />
      </div>
    );
  }

  const selectedProduct = product;
  const hasVariants = Boolean(
    selectedProduct.variants && selectedProduct.variants.length > 0,
  );

  // Selected variant calculation
  const currentVariant = hasVariants
    ? selectedProduct.variants?.find((v) => v.variantKey === selectedVariantKey) ?? null
    : null;

  const currentAvailableStock = currentVariant
    ? currentVariant.availableQuantity
    : selectedProduct.availableStock;

  const isSoldOut = currentAvailableStock === 0;
  const isOwnProduct = Boolean(
    user && selectedProduct.sellerId && user.id === selectedProduct.sellerId
  );

  function add() {
    try {
      if (isOwnProduct) {
        throw new Error("This piece belongs to your atelier and cannot be purchased.");
      }
      if (hasVariants && (!selectedVariantKey || !currentVariant)) {
        throw new Error("Please select a size or variant before adding to bag.");
      }
      if (isSoldOut) {
        throw new Error("This piece is currently out of stock.");
      }
      if (quantity < 1 || quantity > currentAvailableStock) {
        throw new Error(`Select a quantity between 1 and ${currentAvailableStock}.`);
      }
      addToCart(
        selectedProduct,
        quantity,
        currentVariant?.variantKey,
        currentVariant?.id,
      );
      setNotice(
        hasVariants && currentVariant
          ? `Added to your bag (${currentVariant.variantKey} × ${quantity}).`
          : `Added to your bag (${quantity}).`,
      );
      setError("");
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Could not update your bag.",
      );
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-5 sm:px-8 py-8 md:py-16">
      {/* Back to Catalogue Navigation */}
      <div className="mb-8">
        <Link
          to="/products"
          className="inline-flex items-center gap-2 text-xs uppercase tracking-[0.16em] font-medium text-ink/60 hover:text-ink transition"
        >
          ← Back to catalogue
        </Link>
      </div>

      <div className="grid gap-10 md:grid-cols-2 md:gap-16">
        {/* Product Image Section */}
        <div className="aspect-[4/5] bg-[#ECE8E1] overflow-hidden relative">
          {imageError || !selectedProduct.imageUrl ? (
            <div className="flex h-full w-full flex-col items-center justify-center p-8 text-center text-ink/40">
              <svg
                className="h-12 w-12 stroke-1 text-ink/30 mb-3"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="1"
                  d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </svg>
              <span className="text-sm uppercase tracking-wider font-light text-ink/50">
                {selectedProduct.name}
              </span>
            </div>
          ) : (
            <img
              alt={selectedProduct.name}
              className="h-full w-full object-cover"
              onError={() => setImageError(true)}
              src={selectedProduct.imageUrl}
            />
          )}

          {isSoldOut && (
            <span className="absolute left-4 top-4 border border-borderIvory bg-paper/95 px-3 py-1.5 text-xs font-medium uppercase tracking-[0.2em] text-ink/70 backdrop-blur-sm">
              Sold out
            </span>
          )}
        </div>

        {/* Product Details Section */}
        <div className="self-center">
          <p className="eyebrow">
            {selectedProduct.designer} · {selectedProduct.category}
          </p>
          <h1 className="mt-3 font-display text-4xl">{selectedProduct.name}</h1>
          <p className="mt-4 text-lg font-medium">{money(selectedProduct.price)}</p>
          <p className="mt-6 leading-7 text-ink/65">{selectedProduct.description}</p>

          {/* Color Display */}
          {selectedProduct.color && (
            <p className="mt-4 text-xs uppercase tracking-wider text-ink/55">
              Color: <span className="text-ink font-medium capitalize">{selectedProduct.color}</span>
            </p>
          )}

          {/* Variants / Sizes Selection */}
          {hasVariants && (
            <div className="mt-6 border-t border-borderIvory pt-5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold uppercase tracking-wider text-ink/75">
                  Select Size / Variant:
                </span>
                {currentVariant && (
                  <span className="text-ink/55">
                    {currentVariant.availableQuantity > 0
                      ? `${currentVariant.availableQuantity} in stock`
                      : "Sold out"}
                  </span>
                )}
              </div>
              <div className="mt-3 flex flex-wrap gap-2.5">
                {selectedProduct.variants?.map((v) => {
                  const isSelected = selectedVariantKey === v.variantKey;
                  const isAvailable = v.availableQuantity > 0;
                  return (
                    <button
                      key={v.id || v.variantKey}
                      type="button"
                      disabled={!isAvailable}
                      onClick={() => {
                        setSelectedVariantKey(v.variantKey);
                        setQuantity(1);
                        setNotice("");
                      }}
                      className={`min-w-[3rem] px-3.5 py-2 text-xs font-medium uppercase tracking-wider transition ${isSelected
                        ? "bg-ink text-[#F6F3ED] border border-ink"
                        : isAvailable
                          ? "bg-paper border border-borderIvory text-ink hover:border-ink"
                          : "bg-paper/40 border border-borderIvory/50 text-ink/30 cursor-not-allowed line-through"
                        }`}
                    >
                      {v.variantKey}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Stock Availability Indicator or Atelier Ownership Notice */}
          <div className="mt-5">
            {isOwnProduct ? (
              <div className="rounded border border-borderIvory bg-[#F2EFE8]/70 p-4 text-xs leading-relaxed text-ink/80">
                <span className="font-semibold uppercase tracking-wider block mb-1 text-ink">
                  Your Atelier Piece
                </span>
                This piece belongs to your store. You can manage its variants and stock in your{" "}
                <Link to="/seller/products" className="underline font-medium text-ink hover:text-ink/80">
                  Seller Studio
                </Link>
                .
              </div>
            ) : isSoldOut ? (
              <p className="text-sm font-medium text-red-700">
                Currently out of stock{currentVariant ? ` in ${currentVariant.variantKey}` : ""}
              </p>
            ) : (
              <p className="text-sm font-medium text-moss">
                {currentAvailableStock} available
                {currentVariant ? ` in ${currentVariant.variantKey}` : ""}
              </p>
            )}
          </div>

          {/* Add to Bag Controls */}
          {!isSoldOut && !isOwnProduct && (
            <div className="mt-7 flex flex-wrap sm:flex-nowrap max-w-sm gap-3">
              <label className="sr-only" htmlFor="quantity">
                Quantity
              </label>
              <input
                className="field w-20 sm:w-24 text-center shrink-0"
                id="quantity"
                max={currentAvailableStock}
                min={1}
                onChange={(event) => {
                  const val = Number(event.target.value);
                  setQuantity(Math.min(currentAvailableStock, Math.max(1, val)));
                }}
                type="number"
                value={quantity}
              />
              <button
                className="button-primary flex-1 min-w-[140px]"
                onClick={add}
                type="button"
              >
                Add to bag
              </button>
            </div>
          )}

          {error && (
            <div className="mt-4">
              <ErrorMessage>{error}</ErrorMessage>
            </div>
          )}
          {notice && (
            <p className="mt-4 text-sm text-moss" role="status">
              {notice}{" "}
              <Link className="underline font-medium" to="/cart">
                View bag
              </Link>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export function CartPage() {
  const { cart, updateQuantity, removeFromCart } = useMarketplace();
  const [error, setError] = useState("");
  if (!cart.length) return <EmptyState title="Your bag is taking a breather." detail="Find something lovely and it will be waiting here." />;
  return (
    <section className="mx-auto max-w-4xl px-5 sm:px-8 py-10 md:py-16">
      <p className="eyebrow">Your selection</p><h1 className="mt-2 font-display text-4xl">Shopping bag</h1>
      <div className="mt-8 divide-y divide-ink/10">
        {cart.map((item) => {
          const { id, product, quantity, lineTotal, variantKey, availableStock } = item;
          const isOutOfStock = availableStock === 0;
          const isExceeded = quantity > availableStock;
          return (
            <div
              className="flex flex-col sm:grid sm:grid-cols-[6rem_1fr_auto_auto] gap-4 py-5"
              key={id}
            >
              <div className="flex gap-3.5 sm:contents">
                <img
                  alt={product.name}
                  className="h-24 w-20 object-cover shrink-0 sm:h-28 sm:w-24 border border-borderIvory/60 bg-[#ECE8E1]"
                  src={product.imageUrl}
                />
                <div className="flex-1 min-w-0">
                  <Link className="font-medium hover:underline text-sm sm:text-base line-clamp-2" to={`/products/${product.id}`}>
                    {product.name}
                  </Link>
                  <p className="mt-0.5 text-xs sm:text-sm text-ink/55">{product.designer}</p>
                  {variantKey && (
                    <p className="mt-1 text-xs uppercase tracking-wider text-ink/75 font-medium">
                      Size / Variant: <span className="bg-ink/5 border border-ink/10 px-2 py-0.5 rounded text-ink font-semibold">{variantKey}</span>
                    </p>
                  )}
                  {product.color && !variantKey && (
                    <p className="mt-1 text-xs uppercase tracking-wider text-ink/55">
                      Color: <span className="capitalize">{product.color}</span>
                    </p>
                  )}
                  {isOutOfStock ? (
                    <p className="mt-1.5 text-xs text-red-600 font-medium">Currently out of stock</p>
                  ) : isExceeded ? (
                    <p className="mt-1.5 text-xs text-amber-700 font-medium">Only {availableStock} available</p>
                  ) : null}
                  <button
                    className="mt-2.5 hidden sm:inline-block text-xs underline text-ink/65 hover:text-ink transition"
                    onClick={() => removeFromCart(id)}
                    type="button"
                  >
                    Remove
                  </button>
                </div>
              </div>

              {/* Mobile controls row: Qty, remove, price */}
              <div className="flex items-center justify-between border-t border-ink/10 pt-3 sm:border-0 sm:pt-0 sm:contents">
                <div className="flex items-center gap-3 sm:self-start">
                  <label className="text-xs text-ink/55 flex items-center">
                    Qty{" "}
                    <input
                      aria-label={`Quantity for ${product.name}${variantKey ? ` (${variantKey})` : ""}`}
                      className="ml-2 w-14 border border-ink/20 bg-transparent px-2 py-1 text-ink disabled:opacity-50 text-center"
                      disabled={isOutOfStock}
                      max={Math.max(1, availableStock)}
                      min={1}
                      onChange={(event) => {
                        const next = Number(event.target.value);
                        try {
                          updateQuantity(id, next);
                          setError("");
                        } catch (reason) {
                          setError(
                            reason instanceof Error
                              ? reason.message
                              : `Could not update ${product.name}.`,
                          );
                        }
                      }}
                      type="number"
                      value={quantity}
                    />
                  </label>
                  <button
                    className="sm:hidden text-xs underline text-ink/65 hover:text-ink transition"
                    onClick={() => removeFromCart(id)}
                    type="button"
                  >
                    Remove
                  </button>
                </div>
                <span className="self-center sm:self-start text-sm font-semibold text-ink sm:font-medium">
                  {money(lineTotal)}
                </span>
              </div>
            </div>
          );
        })}
      </div>
      {error && <ErrorMessage>{error}</ErrorMessage>}
      <div className="mt-6 flex items-center justify-between border-t border-ink/15 pt-5"><span>Subtotal</span><strong>{money(totalFor(cart))}</strong></div>
      <p className="mt-2 text-xs text-ink/55">Taxes and delivery are not calculated in this demo.</p>
      <Link className="button-primary mt-6 flex justify-center" to="/checkout">Continue to checkout</Link>
    </section>
  );
}

function PasswordEyeIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  );
}

function PasswordEyeOffIcon({ className = "w-4 h-4" }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75} aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
    </svg>
  );
}

export function LoginPage() {
  const { signIn } = useMarketplace();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const markTouched = (field: string) => {
    setTouched((prev) => ({ ...prev, [field]: true }));
  };

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const emailError =
    touched.email && (!email.trim() || !emailRegex.test(email))
      ? "Enter a valid email address."
      : "";
  const passwordError =
    touched.password && !password.trim()
      ? "Enter your password."
      : touched.password && password.length < 8
        ? "Password must be at least 8 characters."
        : "";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    setTouched({
      email: true,
      password: true,
    });

    if (!email.trim() || !emailRegex.test(email)) {
      setError("Please enter a valid email address.");
      return;
    }
    if (!password.trim()) {
      setError("Please enter your password.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setLoading(true);
    try {
      await signIn(email.trim(), password);
      navigate(searchParams.get("next") || "/account/profile");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to sign in.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mx-auto max-w-md px-5 py-16 md:py-24 my-auto w-full">
      <div className="text-center">
        <p className="eyebrow tracking-[0.24em] text-ink/70">THE CLOTHIFY REGISTRY</p>
        <h1 className="mt-2 font-display text-4xl sm:text-5xl font-normal text-ink tracking-tight">
          Welcome Back
        </h1>
        <p className="mt-3 text-sm leading-6 text-ink/65 max-w-sm mx-auto">
          Sign in to continue your Clothify experience.
        </p>
      </div>

      <form className="mt-8 space-y-5" onSubmit={submit} noValidate>
        {/* Email Address */}
        <div>
          <label htmlFor="login-email" className="block text-sm font-medium text-ink">
            Email Address <span className="text-clay">*</span>
          </label>
          <input
            id="login-email"
            type="email"
            autoComplete="email"
            placeholder="Enter your email address"
            className={`field mt-2 ${emailError ? "border-red-400 focus:border-red-600 focus:ring-red-600" : ""}`}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            onBlur={() => markTouched("email")}
            disabled={loading}
          />
          {emailError && <p className="mt-1.5 text-xs text-red-600">{emailError}</p>}
        </div>

        {/* Password */}
        <div>
          <label htmlFor="login-password" className="block text-sm font-medium text-ink">
            Password <span className="text-clay">*</span>
          </label>
          <div className="relative mt-2">
            <input
              id="login-password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              placeholder="Enter your password"
              className={`field pr-12 ${passwordError ? "border-red-400 focus:border-red-600 focus:ring-red-600" : ""}`}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onBlur={() => markTouched("password")}
              disabled={loading}
            />
            <button
              type="button"
              aria-label={showPassword ? "Hide password" : "Show password"}
              aria-pressed={showPassword}
              onClick={() => setShowPassword(!showPassword)}
              className="absolute inset-y-0 right-0 flex items-center pr-3.5 text-ink/50 hover:text-ink focus:outline-none transition-colors"
              disabled={loading}
            >
              {showPassword ? <PasswordEyeOffIcon /> : <PasswordEyeIcon />}
            </button>
          </div>
          {passwordError && <p className="mt-1.5 text-xs text-red-600">{passwordError}</p>}
        </div>

        {/* Global/API Error Message */}
        {error && <ErrorMessage>{error}</ErrorMessage>}

        {/* Submit Button */}
        <button
          id="login-submit-btn"
          type="submit"
          disabled={loading}
          className="button-primary w-full py-4 flex items-center justify-center gap-2 transition-all duration-200 mt-6"
        >
          {loading ? (
            <>
              <span className="w-4 h-4 border-2 border-paper border-t-transparent rounded-full animate-spin" />
              <span>One moment…</span>
            </>
          ) : (
            <span>SIGN IN</span>
          )}
        </button>
      </form>

      {/* Navigation Link to Register */}
      <p className="mt-8 text-center text-sm text-[#242522]">
        Don't have an account yet?{" "}
        <Link
          to={`/register${searchParams.get("next") ? `?next=${encodeURIComponent(searchParams.get("next")!)}` : ""}`}
          className="font-semibold text-[#59664F] underline underline-offset-4 hover:opacity-80 transition-opacity"
        >
          Create an account
        </Link>
      </p>
    </section>
  );
}

export function RegisterPage() {
  const { register } = useMarketplace();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const markTouched = (field: string) => {
    setTouched((prev) => ({ ...prev, [field]: true }));
  };

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const fullNameError = touched.fullName && !fullName.trim() ? "Full name is required." : "";
  const emailError =
    touched.email && (!email.trim() || !emailRegex.test(email))
      ? "Enter a valid email address."
      : "";
  const passwordError =
    touched.password && password.length < 8
      ? "Password must be at least 8 characters."
      : "";
  const confirmPasswordError =
    touched.confirmPassword && confirmPassword !== password
      ? "Passwords do not match."
      : "";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    setTouched({
      fullName: true,
      email: true,
      password: true,
      confirmPassword: true,
    });

    if (!fullName.trim()) {
      setError("Please enter your full name.");
      return;
    }
    if (!email.trim() || !emailRegex.test(email)) {
      setError("Please enter a valid email address.");
      return;
    }
    if (password.length < 8) {
      setError("Password must contain at least 8 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      await register({
        name: fullName.trim(),
        email: email.trim(),
        password,
      });

      const nextTarget = searchParams.get("next") || "/checkout";
      navigate(nextTarget);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Registration could not be completed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mx-auto max-w-xl px-5 py-12 md:py-16">
      <div className="text-center">
        <p className="eyebrow tracking-[0.24em] text-ink/70">THE CLOTHIFY REGISTRY</p>
        <h1 className="mt-2 font-display text-4xl sm:text-5xl font-normal text-ink tracking-tight">
          Create Your Account
        </h1>
        <p className="mt-3 text-sm leading-6 text-ink/65 max-w-md mx-auto">
          Create your personal Clothify account. Shop considered collections, or open your own boutique atelier at any time directly from your profile.
        </p>
      </div>

      <form className="mt-8 space-y-6" onSubmit={submit} noValidate>

        {/* Full Name */}
        <div>
          <label htmlFor="register-fullname" className="block text-sm font-medium text-ink">
            Full Name <span className="text-clay">*</span>
          </label>
          <input
            id="register-fullname"
            type="text"
            autoComplete="name"
            placeholder="e.g. Evelyn Vance"
            className={`field mt-2 ${fullNameError ? "border-red-400 focus:border-red-600 focus:ring-red-600" : ""}`}
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            onBlur={() => markTouched("fullName")}
            disabled={loading}
          />
          {fullNameError && <p className="mt-1.5 text-xs text-red-600">{fullNameError}</p>}
        </div>

        {/* Email Address */}
        <div>
          <label htmlFor="register-email" className="block text-sm font-medium text-ink">
            Email Address <span className="text-clay">*</span>
          </label>
          <input
            id="register-email"
            type="email"
            autoComplete="email"
            placeholder="e.g. evelyn@clothify.luxury"
            className={`field mt-2 ${emailError ? "border-red-400 focus:border-red-600 focus:ring-red-600" : ""}`}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            onBlur={() => markTouched("email")}
            disabled={loading}
          />
          {emailError && <p className="mt-1.5 text-xs text-red-600">{emailError}</p>}
        </div>

        {/* Password */}
        <div>
          <label htmlFor="register-password" className="block text-sm font-medium text-ink">
            Password <span className="text-clay">*</span>
          </label>
          <div className="relative mt-2">
            <input
              id="register-password"
              type={showPassword ? "text" : "password"}
              autoComplete="new-password"
              placeholder="Minimum 8 characters"
              className={`field pr-12 ${passwordError ? "border-red-400 focus:border-red-600 focus:ring-red-600" : ""}`}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onBlur={() => markTouched("password")}
              disabled={loading}
            />
            <button
              type="button"
              aria-label={showPassword ? "Hide password" : "Show password"}
              aria-pressed={showPassword}
              onClick={() => setShowPassword(!showPassword)}
              className="absolute inset-y-0 right-0 flex items-center pr-3.5 text-ink/50 hover:text-ink focus:outline-none transition-colors"
              disabled={loading}
            >
              {showPassword ? <PasswordEyeOffIcon /> : <PasswordEyeIcon />}
            </button>
          </div>
          {passwordError ? (
            <p className="mt-1.5 text-xs text-red-600">{passwordError}</p>
          ) : (
            <p className="mt-1 text-[11px] text-ink/50">Must contain at least 8 characters.</p>
          )}
        </div>

        {/* Confirm Password */}
        <div>
          <label htmlFor="register-confirm-password" className="block text-sm font-medium text-ink">
            Confirm Password <span className="text-clay">*</span>
          </label>
          <div className="relative mt-2">
            <input
              id="register-confirm-password"
              type={showConfirmPassword ? "text" : "password"}
              autoComplete="new-password"
              placeholder="Re-enter your password"
              className={`field pr-12 ${confirmPasswordError ? "border-red-400 focus:border-red-600 focus:ring-red-600" : ""}`}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              onBlur={() => markTouched("confirmPassword")}
              disabled={loading}
            />
            <button
              type="button"
              aria-label={showConfirmPassword ? "Hide confirmation password" : "Show confirmation password"}
              aria-pressed={showConfirmPassword}
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              className="absolute inset-y-0 right-0 flex items-center pr-3.5 text-ink/50 hover:text-ink focus:outline-none transition-colors"
              disabled={loading}
            >
              {showConfirmPassword ? <PasswordEyeOffIcon /> : <PasswordEyeIcon />}
            </button>
          </div>
          {confirmPasswordError && <p className="mt-1.5 text-xs text-red-600">{confirmPasswordError}</p>}
        </div>

        {/* Global/API Error Message */}
        {error && <ErrorMessage>{error}</ErrorMessage>}

        {/* Submit Button */}
        <button
          id="register-submit-btn"
          type="submit"
          disabled={loading}
          className="button-primary w-full py-4 flex items-center justify-center gap-2 transition-all duration-200"
        >
          {loading ? (
            <>
              <span className="w-4 h-4 border-2 border-paper border-t-transparent rounded-full animate-spin" />
              <span>One moment…</span>
            </>
          ) : (
            <span>CREATE ACCOUNT</span>
          )}
        </button>
      </form>

      {/* Navigation Link to Login */}
      <p className="mt-8 text-center text-sm text-ink/65">
        Already a member of Clothify?{" "}
        <Link
          to={`/login${searchParams.get("next") ? `?next=${encodeURIComponent(searchParams.get("next")!)}` : ""}`}
          className="font-semibold text-ink underline underline-offset-4 hover:text-black transition-colors"
        >
          Sign in
        </Link>
      </p>
    </section>
  );
}

export function CheckoutPage() {
  const { cart, user, checkout } = useMarketplace();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  if (!cart.length) return <EmptyState title="Your bag is empty." detail="Add something from the collection before checkout." action="Return to Catalog" to="/products" />;
  if (!user) return (
    <section className="mx-auto max-w-xl px-5 py-12 md:py-16 text-center">
      <p className="eyebrow">One last step</p><h1 className="mt-2 font-display text-4xl">Sign in to continue</h1>
      <p className="mt-4 text-sm text-ink/60">Your bag is ready. Please sign in to complete your order.</p>
      <div className="mt-7 flex justify-center gap-3"><Link className="button-primary" to="/login?next=%2Fcheckout">Sign in</Link><Link className="button-secondary" to="/register?next=%2Fcheckout">Register</Link></div>
    </section>
  );

  async function confirm() {
    if (loading) return;
    setLoading(true);
    setError("");
    try {
      const order = await checkout();
      navigate(`/order-success?order=${encodeURIComponent(order.id)}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not create order. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mx-auto max-w-2xl px-5 py-10 md:py-16">
      <p className="eyebrow">Review before placing</p><h1 className="mt-2 font-display text-4xl">Checkout</h1>
      <p className="mt-3 text-sm text-ink/60">Review your chosen items. Orders will be recorded in pending payment status.</p>
      <div className="mt-8 divide-y divide-ink/10 border-y border-ink/10">
        {cart.map(({ id, product, variantKey, quantity, lineTotal }) => (
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 sm:gap-4 py-4 text-sm" key={id}>
            <div className="min-w-0 flex-1">
              <p className="font-medium text-ink break-words">{product.name}</p>
              {variantKey && (
                <p className="mt-0.5 text-xs text-ink/55 uppercase tracking-wider">
                  Size / Variant: <span className="font-medium text-ink">{variantKey}</span>
                </p>
              )}
            </div>
            <div className="text-right sm:text-right shrink-0 text-xs sm:text-sm">
              <span className="text-ink/60">{quantity} × {money(lineTotal / Math.max(1, quantity))} = </span>
              <strong className="text-ink font-semibold">{money(lineTotal)}</strong>
            </div>
          </div>
        ))}
      </div>
      <div className="flex justify-between py-5"><span>Total Amount</span><strong>{money(totalFor(cart))}</strong></div>
      {error && <ErrorMessage>{error}</ErrorMessage>}
      <button className="button-primary mt-3 w-full" disabled={loading} onClick={confirm} type="button">
        {loading ? "Placing order…" : "Place Order"}
      </button>
    </section>
  );
}

export function OrderSuccessPage() {
  const [searchParams] = useSearchParams();
  const { user } = useMarketplace();
  const orderId = searchParams.get("order");
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    if (!orderId || !user) {
      setLoading(false);
      return () => { active = false; };
    }
    orderService.getOrder(orderId).then((result) => {
      if (active) setOrder(result);
    }).catch((reason: unknown) => {
      if (active) setError(reason instanceof Error ? reason.message : "Could not verify order details.");
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [orderId, user]);

  if (loading) return <Loading label="Checking order details…" />;
  if (error) return <ErrorMessage>{error}</ErrorMessage>;
  if (!order) return <EmptyState title="Order reference not found." detail="This order may belong to another account or does not exist." action="Back to shop" to="/products" />;
  return (
    <section className="mx-auto max-w-xl px-5 sm:px-8 py-10 md:py-16 text-center">
      <p className="eyebrow">Order Placed Successfully</p>
      <h1 className="mt-3 font-display text-3xl sm:text-4xl text-ink font-normal tracking-tight">
        Thank you for your order.
      </h1>
      <p className="mt-4 text-sm leading-6 text-ink/65">
        Your order has been recorded in our system with status <span className="font-semibold text-ink">{order.status}</span>. Total amount: <span className="font-semibold text-ink">{money(order.total)}</span>.
      </p>
      {orderId && (
        <p className="mt-5 text-xs sm:text-sm text-ink/75">
          Order Reference: <strong className="font-mono break-all text-ink font-semibold">{orderId}</strong>
        </p>
      )}
      <div className="mt-7 flex flex-col sm:flex-row justify-center gap-3 max-w-sm mx-auto sm:max-w-none">
        <Link className="button-primary w-full sm:w-auto text-center" to="/account/orders">View my orders</Link>
        <Link className="button-secondary w-full sm:w-auto text-center" to={`/account/orders/${encodeURIComponent(order.id)}`}>Order details</Link>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Helpers & Subcomponents for Orders Experience (Minimal Luxury Aesthetic)
// ---------------------------------------------------------------------------

function formatShortOrderId(orderId: string): string {
  if (!orderId) return "";
  const clean = orderId.replace(/-/g, "").toUpperCase();
  return `#${clean.slice(0, 8)}`;
}

interface OrderStatusConfig {
  label: string;
  badgeClass: string;
}

function getOrderStatusConfig(rawStatus: string): OrderStatusConfig {
  const normalized = String(rawStatus || "").trim().toUpperCase();
  switch (normalized) {
    case "PENDING_PAYMENT":
      return {
        label: "Awaiting Payment",
        badgeClass: "bg-[#F7F3EB] text-[#8C6D3B] border border-[#E4D6BE]",
      };
    case "PAID":
      return {
        label: "Paid",
        badgeClass: "bg-[#EFF3EB] text-[#4A5D43] border border-[#D5E0CF]",
      };
    case "CANCELLED":
      return {
        label: "Cancelled",
        badgeClass: "bg-[#F3F2EE] text-[#7A7873] border border-[#DDD8CE]",
      };
    case "PROCESSING":
      return {
        label: "Processing",
        badgeClass: "bg-[#EDF2F7] text-[#3E5C76] border border-[#CFDFEB]",
      };
    case "SHIPPED":
      return {
        label: "Shipped",
        badgeClass: "bg-[#F1EFF7] text-[#554E74] border border-[#DAD3E8]",
      };
    case "DELIVERED":
      return {
        label: "Delivered",
        badgeClass: "bg-[#EDF6EE] text-[#356142] border border-[#C6E4CF]",
      };
    default: {
      const readable =
        normalized
          .split("_")
          .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
          .join(" ") || "Unknown Status";
      return {
        label: readable,
        badgeClass: "bg-[#F3F2EE] text-[#63625E] border border-[#DDD8CE]",
      };
    }
  }
}

function formatOrderDate(dateString: string): string {
  try {
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return dateString;
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return dateString;
  }
}

function formatOrderDateTime(dateString: string): string {
  try {
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return dateString;
    return d.toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateString;
  }
}

function ProductImagePlaceholder({ className = "w-16 h-20" }: { className?: string }) {
  return (
    <div
      className={`flex items-center justify-center bg-[#ECE8E1] border border-borderIvory text-ink/35 select-none shrink-0 ${className}`}
      aria-label="No image available"
    >
      <svg className="w-5 h-5 stroke-current" fill="none" viewBox="0 0 24 24" strokeWidth="1.25">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M15.75 10.5V6a3.75 3.75 0 10-7.5 0v4.5m11.356-1.993l1.263 12c.07.665-.45 1.243-1.119 1.243H4.25c-.669 0-1.189-.578-1.119-1.243l1.264-12A1.125 1.125 0 015.513 7.5h12.974c.576 0 1.059.435 1.119 1.007zM8.625 10.5a.375.375 0 11-.75 0 .375.375 0 01.75 0zm6.75 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z"
        />
      </svg>
    </div>
  );
}

export function MyOrdersPage() {
  const { user } = useMarketplace();
  const [orders, setOrders] = useState<Order[]>([]);
  const [productsMap, setProductsMap] = useState<Record<string, Product>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    if (!user) {
      setOrders([]);
      setLoading(false);
      return () => {
        active = false;
      };
    }

    Promise.all([
      orderService.getMyOrders(),
      productService.listProducts().catch(() => [] as Product[]),
    ])
      .then(([ordersRes, prodsRes]) => {
        if (!active) return;
        setOrders(ordersRes);
        const map: Record<string, Product> = {};
        for (const p of prodsRes) {
          if (p.id) map[p.id] = p;
        }
        setProductsMap(map);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Could not load orders.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [user]);

  if (!user) {
    return (
      <EmptyState
        title="Sign in to see your orders."
        detail="Orders belong to your authenticated Clothify account."
        action="Sign in"
        to="/login?next=%2Faccount%2Forders"
      />
    );
  }
  if (loading) return <Loading label="Loading orders..." />;
  if (error) return <ErrorMessage>{error}</ErrorMessage>;
  if (!orders.length) {
    return (
      <EmptyState
        title="No orders yet."
        detail="Your next favourite piece is waiting in our collection."
        action="Explore Collection"
        to="/products"
      />
    );
  }

  return (
    <section className="mx-auto max-w-4xl px-5 sm:px-8 py-10 md:py-16">
      {/* Page Header */}
      <div className="mb-8 md:mb-10">
        <p className="eyebrow tracking-[0.22em] text-ink/65">YOUR ACCOUNT</p>
        <h1 className="mt-2 font-display text-4xl sm:text-5xl text-ink font-normal tracking-tight">
          My Orders
        </h1>
        <p className="mt-2 text-sm text-ink/65">Your purchase history</p>
      </div>

      {/* Orders List as Premium Cards */}
      <div className="space-y-6">
        {orders.map((order) => {
          const statusCfg = getOrderStatusConfig(order.status);
          const shortId = formatShortOrderId(order.id);
          const totalPieces = order.items.reduce((sum, it) => sum + (it.quantity || 1), 0);

          return (
            <div
              key={order.id}
              className="border border-borderIvory bg-white/70 shadow-[0_2px_12px_rgba(0,0,0,0.02)] transition duration-200 hover:border-ink/35 hover:bg-white"
            >
              {/* Card Top Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 sm:gap-3 border-b border-borderIvory/80 bg-[#FAF8F5] px-4 sm:px-7 py-3 sm:py-3.5">
                <div className="flex flex-wrap items-center gap-2 sm:gap-4 text-xs">
                  <span className="font-mono font-semibold tracking-wider text-ink text-sm">
                    {shortId}
                  </span>
                  <span className="text-ink/30">|</span>
                  <span className="text-ink/65">{formatOrderDate(order.createdAt)}</span>
                  <span className="text-ink/30">|</span>
                  <span className="text-ink/55">
                    {order.items.length} {order.items.length === 1 ? "line item" : "line items"} (
                    {totalPieces} {totalPieces === 1 ? "piece" : "pieces"})
                  </span>
                </div>

                <div className="self-start sm:self-auto">
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 text-[11px] font-medium uppercase tracking-wider rounded-full ${statusCfg.badgeClass}`}
                  >
                    {statusCfg.label}
                  </span>
                </div>
              </div>

              {/* Card Items List */}
              <div className="p-4 sm:p-7 space-y-4">
                {order.items.map((item, idx) => {
                  const prod = productsMap[item.productId];
                  const productName =
                    prod?.name || (item as any).productName || "Product details unavailable";
                  const variant = item.variantKey || (item as any).variant_key;
                  const itemImg = prod?.imageUrl;
                  const lineTotal =
                    typeof item.lineTotal === "number"
                      ? item.lineTotal
                      : (item.quantity || 1) * (item.unitPrice || 0);

                  return (
                    <div
                      key={item.id || `${order.id}-${idx}`}
                      className="flex items-center gap-3.5 sm:gap-5"
                    >
                      {itemImg ? (
                        <img
                          src={itemImg}
                          alt={productName}
                          className="w-14 h-16 sm:w-16 sm:h-20 max-w-full object-cover border border-borderIvory bg-[#ECE8E1] shrink-0"
                          onError={(e) => {
                            (e.target as HTMLElement).style.display = "none";
                          }}
                        />
                      ) : (
                        <ProductImagePlaceholder className="w-14 h-16 sm:w-16 sm:h-20" />
                      )}

                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm sm:text-base text-ink truncate">
                          {productName}
                        </p>
                        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-ink/60">
                          {variant && (
                            <span className="uppercase tracking-wider">
                              Size / Variant:{" "}
                              <strong className="text-ink font-semibold">{variant}</strong>
                            </span>
                          )}
                          {variant && <span>·</span>}
                          <span>
                            Qty: <strong className="text-ink font-medium">{item.quantity}</strong>
                          </span>
                        </div>
                      </div>

                      <div className="text-right shrink-0">
                        <p className="text-sm font-semibold text-ink">{money(lineTotal)}</p>
                        <p className="text-[11px] text-ink/50 mt-0.5">
                          {money(item.unitPrice)} each
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Card Footer */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4 border-t border-borderIvory/80 bg-[#FCFBF9] px-4 sm:px-7 py-3.5 sm:py-4">
                <div className="flex items-baseline gap-2.5">
                  <span className="text-xs uppercase tracking-wider text-ink/60 font-medium">
                    Order Total:
                  </span>
                  <span className="font-sans text-xl font-semibold text-ink">
                    {money(order.total)}
                  </span>
                </div>

                <div className="flex items-center gap-3">
                  <Link
                    to={`/account/orders/${order.id}`}
                    className="button-secondary text-xs px-6 py-2.5 w-full sm:w-auto inline-flex items-center justify-center gap-1.5 text-center"
                  >
                    View Details →
                  </Link>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

export function OrderDetailPage() {
  const { orderId = "" } = useParams();
  const { user } = useMarketplace();
  const [order, setOrder] = useState<Order | null>(null);
  const [productsMap, setProductsMap] = useState<Record<string, Product>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [cancelling, setCancelling] = useState(false);
  const [cancelError, setCancelError] = useState("");
  const [cancelSuccess, setCancelSuccess] = useState("");
  const [showCancelModal, setShowCancelModal] = useState(false);

  useEffect(() => {
    let active = true;
    if (!user) {
      setLoading(false);
      return () => {
        active = false;
      };
    }
    setLoading(true);
    orderService
      .getOrder(orderId)
      .then((result) => {
        if (active) setOrder(result);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Could not load order details.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [orderId, user]);

  // Load product details for items in the order
  useEffect(() => {
    if (!order || !order.items.length) return;
    const missingIds = order.items
      .map((it) => (it as OrderItem).productId)
      .filter((id) => id && !productsMap[id]);

    if (!missingIds.length) return;

    Promise.all(missingIds.map((id) => productService.getProduct(id).catch(() => null)))
      .then((prods) => {
        setProductsMap((prev) => {
          const next = { ...prev };
          prods.forEach((p) => {
            if (p?.id) next[p.id] = p;
          });
          return next;
        });
      })
      .catch(() => {});
  }, [order]);

  useEffect(() => {
    if (!showCancelModal) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !cancelling) {
        setShowCancelModal(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [showCancelModal, cancelling]);

  const isOwner = Boolean(
    user &&
      order &&
      (
        // Primary check: direct user ID match
        (user.id && order.userId ? user.id === order.userId : false) ||
        // Secondary check: email match if available
        (user.email && order.customerEmail
          ? user.email.toLowerCase() === order.customerEmail.toLowerCase()
          : false) ||
        // Fallback: Backend GET /api/orders/{id} guarantees only owning buyer or seller can view.
        (user.role !== "seller")
      ),
  );

  const isPendingPayment = String(order?.status || "").trim().toUpperCase() === "PENDING_PAYMENT";
  const canCancel = Boolean(isOwner && order && isPendingPayment);

  const handleOpenCancelModal = () => {
    setCancelError("");
    setShowCancelModal(true);
  };

  const handleCloseCancelModal = () => {
    if (cancelling) return;
    setShowCancelModal(false);
  };

  const handleConfirmCancel = async () => {
    if (!order || cancelling) return;

    setCancelling(true);
    setCancelError("");
    setCancelSuccess("");
    try {
      const updated = await orderService.cancelOrder(order.id);
      setOrder(updated);
      setShowCancelModal(false);
      setCancelSuccess("Order has been successfully cancelled and stock restored.");
    } catch (err) {
      setCancelError(err instanceof Error ? err.message : "Failed to cancel order.");
    } finally {
      setCancelling(false);
    }
  };

  const token = authService.getToken();
  if (loading || (token && !user)) return <Loading label="Loading order details..." />;
  if (!user && !token) {
    return (
      <EmptyState
        title="Sign in to view this order."
        detail="Orders belong to your authenticated Clothify account."
        action="Sign in"
        to={`/login?next=%2Faccount%2Forders%2F${encodeURIComponent(orderId)}`}
      />
    );
  }
  if (error) return <ErrorMessage>{error}</ErrorMessage>;
  if (!order) {
    return (
      <EmptyState
        title="Order not found."
        detail="This order may belong to another account or does not exist."
        action="My orders"
        to="/account/orders"
      />
    );
  }

  const statusCfg = getOrderStatusConfig(order.status);
  const shortId = formatShortOrderId(order.id);
  const subtotal = order.items.reduce((sum, item) => {
    const lt =
      typeof item.lineTotal === "number"
        ? item.lineTotal
        : (item.quantity || 1) * (item.unitPrice || 0);
    return sum + lt;
  }, 0);

  const shippingFee = (order.shipment as any)?.shipping_fee ?? (order.shipment as any)?.fee;
  const hasRealShipping = typeof shippingFee === "number" && shippingFee > 0;

  const payment = order.payment;
  const hasPayment = Boolean(
    payment && (payment.payment_type || payment.slip_status || payment.verification_status),
  );

  const shipment = order.shipment;
  const hasShipment = Boolean(
    shipment && (shipment.tracking_number || shipment.carrier_name || shipment.status),
  );

  return (
    <section className="mx-auto max-w-5xl px-4 sm:px-8 py-8 sm:py-10 md:py-16 w-full max-w-full">
      {/* Navigation & Header */}
      <div className="mb-6">
        <Link
          to="/account/orders"
          className="inline-flex items-center gap-1.5 text-xs uppercase tracking-wider text-ink/60 hover:text-ink transition font-medium"
        >
          ← Back to My Orders
        </Link>
      </div>

      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-borderIvory pb-6">
        <div>
          <p className="eyebrow tracking-[0.22em] text-ink/60">ORDER REFERENCE</p>
          <h1 className="mt-1 font-display text-2xl sm:text-3xl md:text-4xl text-ink font-normal tracking-tight">
            Order Details
          </h1>
          <div className="mt-2.5 flex flex-wrap items-center gap-2 sm:gap-3 text-xs text-ink/65">
            <span className="font-mono font-semibold text-ink bg-white/80 border border-borderIvory px-2.5 py-0.5 rounded text-sm break-all">
              {shortId}
            </span>
            <span>·</span>
            <span>Placed on {formatOrderDateTime(order.createdAt)}</span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <span
            className={`inline-flex items-center px-3.5 py-1 text-xs uppercase tracking-wider font-medium rounded-full ${statusCfg.badgeClass}`}
          >
            {statusCfg.label}
          </span>
        </div>
      </div>

      {/* Main Responsive Grid Layout */}
      <div className="mt-8 grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-8 items-start w-full max-w-full">
        {/* Left Column: Products List & Details */}
        <div className="space-y-6 min-w-0 max-w-full">
          {/* Items Card */}
          <div className="border border-borderIvory bg-white/70 p-4 sm:p-7 shadow-[0_2px_12px_rgba(0,0,0,0.02)] max-w-full">
            <h2 className="font-display text-xl text-ink font-normal pb-4 border-b border-borderIvory/70">
              Items in this Order ({order.items.length})
            </h2>

            <div className="divide-y divide-borderIvory/70">
              {order.items.map((item, idx) => {
                const prod = productsMap[item.productId];
                const productName =
                  prod?.name || (item as any).productName || "Product details unavailable";
                const variant = item.variantKey || (item as any).variant_key;
                const itemImg = prod?.imageUrl;
                const lineTotal =
                  typeof item.lineTotal === "number"
                    ? item.lineTotal
                    : (item.quantity || 1) * (item.unitPrice || 0);

                return (
                  <div
                    key={item.id || `${order.id}-${idx}`}
                    className="py-4 sm:py-5 first:pt-4 last:pb-0 flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-6 min-w-0"
                  >
                    <div className="flex items-start sm:items-center gap-3.5 sm:gap-5 flex-1 min-w-0">
                      {itemImg ? (
                        <img
                          src={itemImg}
                          alt={productName}
                          className="w-16 h-20 sm:w-20 sm:h-24 max-w-full object-cover border border-borderIvory bg-[#ECE8E1] shrink-0"
                          onError={(e) => {
                            (e.target as HTMLElement).style.display = "none";
                          }}
                        />
                      ) : (
                        <ProductImagePlaceholder className="w-16 h-20 sm:w-20 sm:h-24" />
                      )}

                      <div className="flex-1 min-w-0 space-y-1">
                        <p className="font-medium text-sm sm:text-base text-ink break-words leading-snug">
                          {productName}
                        </p>
                        {variant && (
                          <p className="text-xs text-ink/65 uppercase tracking-wider break-words">
                            Variant / Size:{" "}
                            <strong className="text-ink font-semibold">{variant}</strong>
                          </p>
                        )}
                        <p className="text-xs text-ink/55">
                          Quantity: <span className="font-medium text-ink">{item.quantity}</span> ×{" "}
                          {money(item.unitPrice)}
                        </p>
                      </div>
                    </div>

                    <div className="flex sm:flex-col justify-between sm:justify-center items-baseline sm:items-end pt-2 sm:pt-0 border-t border-borderIvory/50 sm:border-t-0 shrink-0">
                      <span className="sm:hidden text-xs text-ink/50 uppercase tracking-wider font-light">
                        Line Total
                      </span>
                      <p className="text-sm sm:text-base font-semibold text-ink">
                        {money(lineTotal)}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Payment Information (shown only if real data exists) */}
          {hasPayment && (
            <div className="border border-borderIvory bg-white/70 p-5 sm:p-6 shadow-[0_2px_12px_rgba(0,0,0,0.02)]">
              <h3 className="font-display text-lg text-ink font-normal pb-3 border-b border-borderIvory/70">
                Payment Details
              </h3>
              <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                {payment?.payment_type && (
                  <div>
                    <span className="text-ink/50 uppercase tracking-wider block text-[10px]">
                      Payment Method
                    </span>
                    <span className="font-medium text-ink mt-1 block">
                      {String(payment.payment_type).replace(/_/g, " ")}
                    </span>
                  </div>
                )}
                {(payment?.slip_status || payment?.verification_status) && (
                  <div>
                    <span className="text-ink/50 uppercase tracking-wider block text-[10px]">
                      Verification Status
                    </span>
                    <span className="font-medium text-ink mt-1 block capitalize">
                      {String(payment.slip_status || payment.verification_status)
                        .toLowerCase()
                        .replace(/_/g, " ")}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Shipment Information: multi-package per seller or single legacy shipment */}
          {Array.isArray(order.shipments) && order.shipments.length > 1 ? (
            <div className="border border-borderIvory bg-white/70 p-5 sm:p-6 shadow-[0_2px_12px_rgba(0,0,0,0.02)] space-y-4">
              <h3 className="font-display text-lg text-ink font-normal pb-3 border-b border-borderIvory/70">
                Shipment & Delivery ({order.shipments.length} Packages)
              </h3>
              <div className="space-y-4">
                {order.shipments.map((shp: any, idx: number) => (
                  <div key={shp.id || idx} className="p-4 bg-[#FBF9F5] border border-borderIvory/60 space-y-3">
                    <div className="flex justify-between items-center pb-2 border-b border-borderIvory/40">
                      <span className="text-xs font-semibold uppercase tracking-wider text-ink/70">
                        Package #{idx + 1}
                      </span>
                      <span className="inline-block px-2 py-0.5 text-[10px] uppercase font-medium tracking-wider bg-goldIvory/40 text-ink">
                        {String(shp.status || "PREPARING").toLowerCase().replace(/_/g, " ")}
                      </span>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                      <div>
                        <span className="text-ink/50 uppercase tracking-wider block text-[10px]">Carrier</span>
                        <span className="font-medium text-ink mt-0.5 block">{shp.carrier_name || "Standard Delivery"}</span>
                      </div>
                      <div>
                        <span className="text-ink/50 uppercase tracking-wider block text-[10px]">Tracking Number</span>
                        <span className="font-mono font-medium text-ink mt-0.5 block">{shp.tracking_number || "Preparing shipment..."}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            hasShipment && (
              <div className="border border-borderIvory bg-white/70 p-5 sm:p-6 shadow-[0_2px_12px_rgba(0,0,0,0.02)]">
                <h3 className="font-display text-lg text-ink font-normal pb-3 border-b border-borderIvory/70">
                  Shipment & Delivery
                </h3>
                <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                  {shipment?.carrier_name && (
                    <div>
                      <span className="text-ink/50 uppercase tracking-wider block text-[10px]">
                        Carrier
                      </span>
                      <span className="font-medium text-ink mt-1 block">
                        {shipment.carrier_name}
                      </span>
                    </div>
                  )}
                  {shipment?.tracking_number && (
                    <div>
                      <span className="text-ink/50 uppercase tracking-wider block text-[10px]">
                        Tracking Number
                      </span>
                      <span className="font-mono font-medium text-ink mt-1 block">
                        {shipment.tracking_number}
                      </span>
                    </div>
                  )}
                  {shipment?.status && (
                    <div>
                      <span className="text-ink/50 uppercase tracking-wider block text-[10px]">
                        Shipment Status
                      </span>
                      <span className="font-medium text-ink mt-1 block capitalize">
                        {String(shipment.status).toLowerCase().replace(/_/g, " ")}
                      </span>
                    </div>
                  )}
                  {shipment?.estimated_delivery && (
                    <div>
                      <span className="text-ink/50 uppercase tracking-wider block text-[10px]">
                        Estimated Delivery
                      </span>
                      <span className="font-medium text-ink mt-1 block">
                        {formatOrderDate(shipment.estimated_delivery)}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )
          )}

        </div>

        {/* Right Column: Order Summary Card */}
        <div className="sticky top-28 space-y-6">
          <div className="border border-borderIvory bg-[#FBF9F5] p-6 shadow-[0_2px_12px_rgba(0,0,0,0.02)]">
            <h2 className="font-display text-xl text-ink font-normal pb-3.5 border-b border-borderIvory">
              Order Summary
            </h2>

            <div className="mt-4 space-y-3 text-xs">
              <div className="flex justify-between items-center text-ink/75">
                <span>Subtotal</span>
                <span className="font-medium text-ink">{money(subtotal)}</span>
              </div>

              {hasRealShipping && (
                <div className="flex justify-between items-center text-ink/75">
                  <span>Shipping</span>
                  <span className="font-medium text-ink">{money(shippingFee)}</span>
                </div>
              )}

              <div className="border-t border-borderIvory/80 pt-3 flex justify-between items-baseline">
                <span className="text-sm font-semibold text-ink">Total Amount</span>
                <span className="font-sans text-lg font-bold text-ink">
                  {money(order.total)}
                </span>
              </div>
            </div>

            {isPendingPayment && isOwner && (
              <div className="pt-3 border-t border-borderIvory/70">
                <Link
                  to={`/account/orders/${order.id}/pay`}
                  id="pay-now-summary-btn"
                  className="button-primary w-full text-xs py-3 text-center block"
                >
                  Pay Now
                </Link>
              </div>
            )}

            <div className="mt-5 pt-4 border-t border-borderIvory/60 text-[11px] leading-relaxed text-ink/55">
              Prices include all applicable taxes and handling. Thoughtfully curated by Clothify
              Atelier.
            </div>
          </div>
        </div>
      </div>

      {/* Cancellation Section (Placed at the end after Order Summary & Pay Now) */}
      {canCancel && (
        <div
          id="cancel-order-section"
          className="mt-8 border border-borderIvory bg-white/70 p-5 sm:p-6 shadow-[0_2px_12px_rgba(0,0,0,0.02)] flex flex-col sm:flex-row sm:items-center justify-between gap-4"
        >
          <div>
            <p className="text-sm font-semibold text-ink">Cancel this order</p>
            <p className="text-xs text-ink/60 mt-0.5">
              Cancel your unpaid order to release items back to inventory.
            </p>
          </div>
          <button
            id="cancel-order-button"
            type="button"
            onClick={handleOpenCancelModal}
            disabled={cancelling}
            className="inline-flex items-center justify-center rounded border border-rose-300 bg-white px-5 py-2.5 text-xs font-semibold text-rose-700 hover:bg-rose-50 disabled:opacity-50 transition shrink-0"
          >
            Cancel Order
          </button>
        </div>
      )}

      {cancelError && !showCancelModal && (
        <div className="mt-4 rounded border border-rose-200 bg-rose-50 p-3.5 text-xs text-rose-700">
          {cancelError}
        </div>
      )}

      {cancelSuccess && (
        <div className="mt-4 rounded border border-emerald-200 bg-emerald-50 p-3.5 text-xs text-emerald-800">
          {cancelSuccess}
        </div>
      )}

      {/* Custom Confirmation Modal */}
      {showCancelModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-labelledby="cancel-modal-title"
          onClick={handleCloseCancelModal}
        >
          <div
            className="w-full max-w-md rounded-2xl bg-white p-6 sm:p-7 shadow-2xl border border-ink/10 transition-all text-center"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Warning Icon */}
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-rose-50 text-rose-600 ring-8 ring-rose-50/60">
              <svg
                className="h-7 w-7"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth="2"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                />
              </svg>
            </div>

            {/* Title & Messages */}
            <h3 id="cancel-modal-title" className="font-display text-2xl text-ink">
              Cancel Order?
            </h3>
            <p className="mt-2 text-sm font-medium text-ink">
              Are you sure you want to cancel this order?
            </p>
            <p className="mt-1 text-xs text-ink/60">The reserved inventory will be restored.</p>

            {/* Inline Error inside modal */}
            {cancelError && (
              <div className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700 text-left">
                {cancelError}
              </div>
            )}

            {/* Modal Actions */}
            <div className="mt-6 flex flex-col-reverse sm:flex-row gap-3 sm:justify-end">
              <button
                type="button"
                id="cancel-modal-keep-btn"
                onClick={handleCloseCancelModal}
                disabled={cancelling}
                className="inline-flex w-full sm:w-auto items-center justify-center rounded-lg border border-ink/15 bg-white px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-ink hover:bg-stone-50 disabled:opacity-50 transition"
              >
                Keep Order
              </button>
              <button
                type="button"
                id="cancel-modal-confirm-btn"
                onClick={handleConfirmCancel}
                disabled={cancelling}
                className="inline-flex w-full sm:w-auto items-center justify-center rounded-lg bg-rose-600 px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-white shadow-sm hover:bg-rose-700 disabled:opacity-50 transition"
              >
                {cancelling ? (
                  <span className="inline-flex items-center gap-2">
                    <svg className="h-3.5 w-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8v8H4z"
                      />
                    </svg>
                    Cancelling order...
                  </span>
                ) : (
                  "Yes, Cancel Order"
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

export function PaymentPage() {
  const { orderId = "" } = useParams();
  const { user } = useMarketplace();
  const [order, setOrder] = useState<Order | null>(null);
  const [productsMap, setProductsMap] = useState<Record<string, Product>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Workflow states: "method" | "confirm" | "processing" | "success" | "failed"
  const [step, setStep] = useState<"method" | "confirm" | "processing" | "success" | "failed">(
    "method",
  );
  const [paymentMethod, setPaymentMethod] = useState<string>("SIMULATED_CARD");
  const [simulateOutcome, setSimulateOutcome] = useState<"SUCCESS" | "FAILURE">("SUCCESS");
  const [processing, setProcessing] = useState(false);
  const [paymentErrorMsg, setPaymentErrorMsg] = useState("");

  useEffect(() => {
    let active = true;
    if (!user) {
      setLoading(false);
      return () => {
        active = false;
      };
    }
    setLoading(true);
    orderService
      .getOrder(orderId)
      .then((res) => {
        if (active) setOrder(res);
      })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : "Failed to load order.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [orderId, user]);

  useEffect(() => {
    if (!order || !order.items.length) return;
    const missing = order.items
      .map((it) => (it as OrderItem).productId)
      .filter((id) => id && !productsMap[id]);
    if (!missing.length) return;

    Promise.all(missing.map((id) => productService.getProduct(id).catch(() => null)))
      .then((prods) => {
        setProductsMap((prev) => {
          const next = { ...prev };
          prods.forEach((p) => {
            if (p?.id) next[p.id] = p;
          });
          return next;
        });
      })
      .catch(() => {});
  }, [order]);

  const token = authService.getToken();
  if (loading || (token && !user)) return <Loading label="Loading order for simulated payment..." />;
  if (!user && !token) {
    return (
      <EmptyState
        title="Sign in to complete payment."
        detail="Payment requires an authenticated Clothify account."
        action="Sign in"
        to={`/login?next=%2Faccount%2Forders%2F${encodeURIComponent(orderId)}%2Fpay`}
      />
    );
  }
  if (error) return <ErrorMessage>{error}</ErrorMessage>;
  if (!order) {
    return (
      <EmptyState
        title="Order not found."
        detail="The requested order could not be located."
        action="My orders"
        to="/account/orders"
      />
    );
  }

  // If order is cancelled
  if (order.status === "CANCELLED") {
    return (
      <section className="mx-auto max-w-xl px-5 py-16 text-center">
        <div className="border border-borderIvory bg-white/70 p-8 shadow-[0_2px_12px_rgba(0,0,0,0.02)]">
          <p className="eyebrow text-rose-700">ORDER CANCELLED</p>
          <h1 className="mt-2 font-display text-3xl text-ink font-normal">
            Cannot Pay for Cancelled Order
          </h1>
          <p className="mt-3 text-sm text-ink/65 leading-relaxed">
            This order was previously cancelled and the reserved inventory has been released.
          </p>
          <div className="mt-6 flex justify-center gap-3">
            <Link to={`/account/orders/${order.id}`} className="button-secondary text-xs">
              View Order Details
            </Link>
            <Link to="/account/orders" className="button-primary text-xs">
              My Orders
            </Link>
          </div>
        </div>
      </section>
    );
  }

  // If order is already paid and not in the immediate success screen
  if (order.status === "PAID" && step !== "success") {
    return (
      <section className="mx-auto max-w-xl px-5 py-16 text-center">
        <div className="border border-borderIvory bg-white/70 p-8 shadow-[0_2px_12px_rgba(0,0,0,0.02)]">
          <p className="eyebrow text-moss">ORDER ALREADY PAID</p>
          <h1 className="mt-2 font-display text-3xl text-ink font-normal">
            Payment Already Verified
          </h1>
          <p className="mt-3 text-sm text-ink/65 leading-relaxed">
            This order has already been paid and is being prepared for fulfillment.
          </p>
          <div className="mt-6 flex justify-center gap-3">
            <Link to={`/account/orders/${order.id}`} className="button-primary text-xs">
              View Order Details
            </Link>
          </div>
        </div>
      </section>
    );
  }

  const shortId = formatShortOrderId(order.id);
  const subtotal = order.items.reduce((sum, item) => {
    const lt =
      typeof item.lineTotal === "number"
        ? item.lineTotal
        : (item.quantity || 1) * (item.unitPrice || 0);
    return sum + lt;
  }, 0);

  const handleConfirmAndPay = async () => {
    if (processing || !order) return;
    setProcessing(true);
    setStep("processing");
    setPaymentErrorMsg("");

    try {
      // Small simulated latency for natural luxury UX
      await new Promise((r) => setTimeout(r, 600));

      const res = await orderService.simulatePayment(order.id, {
        outcome: simulateOutcome,
        paymentMethod,
        failureReason:
          simulateOutcome === "FAILURE"
            ? "Simulated card authorization declined (demonstration failure scenario)."
            : undefined,
      });

      setOrder(res.order);
      if (res.success && res.order.status === "PAID") {
        setStep("success");
      } else {
        setPaymentErrorMsg(
          res.message || "Simulated payment declined as requested for demonstration.",
        );
        setStep("failed");
      }
    } catch (err) {
      setPaymentErrorMsg(err instanceof Error ? err.message : "Payment processing error.");
      setStep("failed");
    } finally {
      setProcessing(false);
    }
  };

  // -------------------------------------------------------------
  // Screen 3: Processing Payment
  // -------------------------------------------------------------
  if (step === "processing") {
    return (
      <section className="mx-auto max-w-lg px-5 py-20 text-center">
        <div className="border border-borderIvory bg-white/80 p-8 sm:p-12 shadow-[0_2px_16px_rgba(0,0,0,0.03)]">
          <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-[#FAF8F5] text-ink border border-borderIvory">
            <svg className="h-8 w-8 animate-spin text-ink" viewBox="0 0 24 24" fill="none">
              <circle
                className="opacity-20"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="3"
              />
              <path className="opacity-80" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
          </div>
          <p className="eyebrow tracking-[0.22em] text-ink/65">SIMULATED PAYMENT</p>
          <h2 className="mt-2 font-display text-3xl text-ink font-normal">Processing Payment</h2>
          <p className="mt-3 text-sm text-ink/65 leading-relaxed">
            Verifying your demonstration transaction with Clothify Atelier. Please do not refresh
            or close this window.
          </p>
          <div className="mt-6 pt-5 border-t border-borderIvory/70 text-xs text-ink/50 font-mono">
            Order Reference: {shortId} · Amount: {money(order.total)}
          </div>
        </div>
      </section>
    );
  }

  // -------------------------------------------------------------
  // Screen 4: Payment Successful
  // -------------------------------------------------------------
  if (step === "success") {
    return (
      <section className="mx-auto max-w-xl px-5 py-16 text-center">
        <div className="border border-borderIvory bg-white/80 p-8 sm:p-12 shadow-[0_2px_16px_rgba(0,0,0,0.03)]">
          {/* Success Icon */}
          <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-[#EFF3EB] text-[#4A5D43] ring-8 ring-[#EFF3EB]/50">
            <svg
              className="h-8 w-8"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth="2"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
            </svg>
          </div>

          <p className="eyebrow tracking-[0.22em] text-[#4A5D43]">DEMONSTRATION COMPLETE</p>
          <h1 className="mt-2 font-display text-3xl sm:text-4xl text-ink font-normal tracking-tight">
            Payment Successful
          </h1>
          <p className="mt-3 text-sm text-ink/70 leading-relaxed max-w-md mx-auto">
            Your simulated payment has been successfully recorded and verified by the backend. No
            real money was charged.
          </p>

          <div className="mt-8 border-y border-borderIvory/70 py-4 my-6 bg-[#FAF8F5] flex flex-wrap items-center justify-around gap-4 text-xs">
            <div>
              <span className="text-ink/50 uppercase tracking-wider block text-[10px]">
                Order Ref
              </span>
              <span className="font-mono font-semibold text-ink text-sm mt-0.5 block">
                {shortId}
              </span>
            </div>
            <div>
              <span className="text-ink/50 uppercase tracking-wider block text-[10px]">
                Total Paid
              </span>
              <span className="font-sans font-bold text-ink text-base mt-0.5 block">
                {money(order.total)}
              </span>
            </div>
            <div>
              <span className="text-ink/50 uppercase tracking-wider block text-[10px]">
                Status
              </span>
              <span className="inline-flex items-center px-2.5 py-0.5 text-[11px] font-medium uppercase tracking-wider rounded-full bg-[#EFF3EB] text-[#4A5D43] border border-[#D5E0CF]">
                Paid
              </span>
            </div>
          </div>

          <div className="mt-8 flex flex-col sm:flex-row justify-center gap-3.5">
            <Link
              to={`/account/orders/${order.id}`}
              id="view-order-details-success-btn"
              className="button-primary text-xs px-7 py-3 w-full sm:w-auto text-center"
            >
              View Order Details →
            </Link>
            <Link
              to="/account/orders"
              id="back-my-orders-success-btn"
              className="button-secondary text-xs px-7 py-3 w-full sm:w-auto text-center"
            >
              Back to My Orders
            </Link>
          </div>
        </div>
      </section>
    );
  }

  // -------------------------------------------------------------
  // Screen 5: Payment Failed
  // -------------------------------------------------------------
  if (step === "failed") {
    return (
      <section className="mx-auto max-w-xl px-5 py-16 text-center">
        <div className="border border-borderIvory bg-white/80 p-8 sm:p-12 shadow-[0_2px_16px_rgba(0,0,0,0.03)]">
          {/* Failure Icon */}
          <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-rose-50 text-rose-600 ring-8 ring-rose-50/60">
            <svg
              className="h-8 w-8"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth="2"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>

          <p className="eyebrow tracking-[0.22em] text-rose-700">SIMULATED DECLINE</p>
          <h1 className="mt-2 font-display text-3xl sm:text-4xl text-ink font-normal tracking-tight">
            Payment Failed
          </h1>
          <p className="mt-3 text-sm text-ink/70 leading-relaxed max-w-md mx-auto">
            {paymentErrorMsg ||
              "The simulated payment was declined for demonstration testing purposes. This is a simulation result — no real bank was contacted and no funds were deducted."}
          </p>
          <p className="mt-2 text-xs text-ink/55">
            Your order remains in <strong className="text-ink font-medium">Awaiting Payment</strong>{" "}
            status and your reserved inventory is safe.
          </p>

          <div className="mt-6 border-y border-borderIvory/70 py-3.5 bg-[#FAF8F5] text-xs font-mono text-ink/65">
            Order Reference: {shortId} · Amount: {money(order.total)}
          </div>

          <div className="mt-8 flex flex-col sm:flex-row justify-center gap-3.5">
            <button
              type="button"
              id="try-again-btn"
              onClick={() => {
                setSimulateOutcome("SUCCESS");
                setStep("method");
              }}
              className="button-primary text-xs px-7 py-3 w-full sm:w-auto text-center"
            >
              Try Again
            </button>
            <Link
              to={`/account/orders/${order.id}`}
              id="back-order-details-failed-btn"
              className="button-secondary text-xs px-7 py-3 w-full sm:w-auto text-center"
            >
              Back to Order Details
            </Link>
          </div>
        </div>
      </section>
    );
  }

  // -------------------------------------------------------------
  // Screen 2: Payment Confirmation
  // -------------------------------------------------------------
  if (step === "confirm") {
    return (
      <section className="mx-auto max-w-2xl px-5 sm:px-8 py-10 md:py-16">
        <div className="mb-6">
          <button
            type="button"
            onClick={() => setStep("method")}
            className="inline-flex items-center gap-1.5 text-xs uppercase tracking-wider text-ink/60 hover:text-ink transition font-medium"
          >
            ← Back to Payment Methods
          </button>
        </div>

        <div className="border border-borderIvory bg-white/80 p-6 sm:p-9 shadow-[0_2px_14px_rgba(0,0,0,0.02)]">
          <p className="eyebrow tracking-[0.22em] text-ink/60">STEP 2 OF 2 · CONFIRMATION</p>
          <h1 className="mt-2 font-display text-3xl sm:text-4xl text-ink font-normal tracking-tight">
            Confirm Payment
          </h1>

          {/* Prominent Demonstration Notice */}
          <div className="mt-6 rounded-sm border border-[#E3D3BA] bg-[#FAF6EE] p-4 text-xs text-[#7A5B28] leading-relaxed">
            <div className="flex items-start gap-2.5">
              <svg
                className="w-4 h-4 shrink-0 mt-0.5 text-[#8C6D3B]"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
              <div>
                <strong className="font-semibold block">Demonstration Notice:</strong>
                This is a simulated payment for demonstration purposes. No real money will be
                charged.
              </div>
            </div>
          </div>

          {/* Summary Box */}
          <div className="mt-6 border border-borderIvory/80 bg-[#FAF8F5] p-5 rounded-sm space-y-3.5 text-xs">
            <div className="flex justify-between items-center text-ink/75">
              <span>Order Reference</span>
              <span className="font-mono font-semibold text-ink text-sm">{shortId}</span>
            </div>
            <div className="flex justify-between items-center text-ink/75">
              <span>Selected Method</span>
              <span className="font-medium text-ink">
                {paymentMethod === "SIMULATED_PROMPTPAY"
                  ? "Simulated PromptPay / QR"
                  : "Simulated Credit / Debit Card"}
              </span>
            </div>
            <div className="flex justify-between items-center text-ink/75">
              <span>Simulation Outcome Mode</span>
              <span
                className={`font-semibold ${
                  simulateOutcome === "FAILURE" ? "text-rose-700" : "text-[#4A5D43]"
                }`}
              >
                {simulateOutcome === "FAILURE" ? "Simulate Decline (Failure)" : "Simulate Success"}
              </span>
            </div>
            <div className="border-t border-borderIvory pt-3 flex justify-between items-baseline">
              <span className="text-sm font-semibold text-ink">Total Amount</span>
              <span className="font-sans text-xl font-bold text-ink">{money(order.total)}</span>
            </div>
          </div>

          <div className="mt-8 flex flex-col-reverse sm:flex-row justify-end gap-3.5 border-t border-borderIvory/70 pt-6">
            <button
              type="button"
              onClick={() => setStep("method")}
              className="button-secondary text-xs px-6 py-3 w-full sm:w-auto text-center"
            >
              Back
            </button>
            <button
              type="button"
              id="confirm-and-pay-btn"
              onClick={handleConfirmAndPay}
              className="button-primary text-xs px-7 py-3 w-full sm:w-auto text-center"
            >
              Confirm & Pay ({money(order.total)})
            </button>
          </div>
        </div>
      </section>
    );
  }

  // -------------------------------------------------------------
  // Screen 1: Payment Method (Default)
  // -------------------------------------------------------------
  return (
    <section className="mx-auto max-w-5xl px-5 sm:px-8 py-10 md:py-16">
      {/* Navigation */}
      <div className="mb-6">
        <Link
          to={`/account/orders/${order.id}`}
          className="inline-flex items-center gap-1.5 text-xs uppercase tracking-wider text-ink/60 hover:text-ink transition font-medium"
        >
          ← Back to Order Details
        </Link>
      </div>

      {/* Header */}
      <div className="border-b border-borderIvory pb-6">
        <p className="eyebrow tracking-[0.22em] text-ink/60">STEP 1 OF 2 · PAYMENT METHOD</p>
        <h1 className="mt-1 font-display text-3xl sm:text-4xl text-ink font-normal tracking-tight">
          Select Payment Method
        </h1>
        <div className="mt-2.5 flex flex-wrap items-center gap-2 sm:gap-3 text-xs text-ink/65">
          <span className="font-mono font-semibold text-ink bg-white/80 border border-borderIvory px-2.5 py-0.5 rounded text-sm">
            {shortId}
          </span>
          <span>·</span>
          <span>Placed on {formatOrderDate(order.createdAt)}</span>
          <span>·</span>
          <span>Status: Awaiting Payment</span>
        </div>
      </div>

      {/* 2-Column Responsive Layout */}
      <div className="mt-8 grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-8 items-start">
        {/* Left Column: Payment Options */}
        <div className="space-y-6">
          <div className="border border-borderIvory bg-white/70 p-6 sm:p-7 shadow-[0_2px_12px_rgba(0,0,0,0.02)]">
            <h2 className="font-display text-xl text-ink font-normal pb-4 border-b border-borderIvory/70">
              Payment Options
            </h2>

            <div className="mt-5 space-y-3">
              {/* Option 1: Simulated Card */}
              <label
                className={`flex items-start gap-3.5 p-4 border rounded-sm cursor-pointer transition ${
                  paymentMethod === "SIMULATED_CARD"
                    ? "border-ink bg-[#FAF8F5] shadow-xs"
                    : "border-borderIvory hover:border-ink/40 bg-white/50"
                }`}
              >
                <input
                  type="radio"
                  name="paymentMethod"
                  value="SIMULATED_CARD"
                  checked={paymentMethod === "SIMULATED_CARD"}
                  onChange={() => setPaymentMethod("SIMULATED_CARD")}
                  className="mt-1 text-ink focus:ring-ink"
                />
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-sm text-ink">
                      Simulated Credit / Debit Card
                    </span>
                    <span className="text-[10px] uppercase tracking-wider font-mono text-ink/50 bg-[#ECE8E1] px-1.5 py-0.5 rounded">
                      Demo
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-ink/65 leading-relaxed">
                    Instant simulated card authorization. No real card details or bank connections
                    are involved.
                  </p>
                </div>
              </label>

              {/* Option 2: Simulated PromptPay / QR */}
              <label
                className={`flex items-start gap-3.5 p-4 border rounded-sm cursor-pointer transition ${
                  paymentMethod === "SIMULATED_PROMPTPAY"
                    ? "border-ink bg-[#FAF8F5] shadow-xs"
                    : "border-borderIvory hover:border-ink/40 bg-white/50"
                }`}
              >
                <input
                  type="radio"
                  name="paymentMethod"
                  value="SIMULATED_PROMPTPAY"
                  checked={paymentMethod === "SIMULATED_PROMPTPAY"}
                  onChange={() => setPaymentMethod("SIMULATED_PROMPTPAY")}
                  className="mt-1 text-ink focus:ring-ink"
                />
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-sm text-ink">
                      Simulated PromptPay / Instant QR
                    </span>
                    <span className="text-[10px] uppercase tracking-wider font-mono text-ink/50 bg-[#ECE8E1] px-1.5 py-0.5 rounded">
                      Demo
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-ink/65 leading-relaxed">
                    Instant simulated QR code validation without actual banking API interactions.
                  </p>
                </div>
              </label>
            </div>
          </div>

          {/* Testing Outcome Simulation Selector */}
          <div className="border border-borderIvory bg-[#FBF9F5] p-5 sm:p-6 rounded-sm">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-xs uppercase tracking-wider text-ink">
                Test Simulation Outcome
              </h3>
              <span className="text-[10px] uppercase font-mono text-ink/50 bg-[#ECE8E1] px-2 py-0.5 rounded">
                Developer / Demo Mode
              </span>
            </div>
            <p className="text-xs text-ink/60 mb-3.5">
              Choose the simulated response from the backend to verify both success and failure
              states:
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <label
                className={`p-3 border rounded-sm cursor-pointer transition flex items-center gap-2.5 ${
                  simulateOutcome === "SUCCESS"
                    ? "border-[#4A5D43] bg-[#EFF3EB] text-[#4A5D43] font-semibold"
                    : "border-borderIvory bg-white text-ink/75"
                }`}
              >
                <input
                  type="radio"
                  name="simulateOutcome"
                  value="SUCCESS"
                  checked={simulateOutcome === "SUCCESS"}
                  onChange={() => setSimulateOutcome("SUCCESS")}
                  className="text-[#4A5D43] focus:ring-[#4A5D43]"
                />
                <span>Simulate Success (Order → PAID)</span>
              </label>

              <label
                className={`p-3 border rounded-sm cursor-pointer transition flex items-center gap-2.5 ${
                  simulateOutcome === "FAILURE"
                    ? "border-rose-300 bg-rose-50 text-rose-700 font-semibold"
                    : "border-borderIvory bg-white text-ink/75"
                }`}
              >
                <input
                  type="radio"
                  name="simulateOutcome"
                  value="FAILURE"
                  checked={simulateOutcome === "FAILURE"}
                  onChange={() => setSimulateOutcome("FAILURE")}
                  className="text-rose-600 focus:ring-rose-600"
                />
                <span>Simulate Failure (Order remains Pending)</span>
              </label>
            </div>
          </div>

          {/* Navigation Buttons */}
          <div className="flex flex-col sm:flex-row justify-between items-center gap-4 pt-2">
            <Link
              to={`/account/orders/${order.id}`}
              className="button-secondary text-xs px-6 py-3 w-full sm:w-auto text-center"
            >
              ← Back to Order Details
            </Link>
            <button
              type="button"
              id="continue-to-payment-btn"
              onClick={() => setStep("confirm")}
              className="button-primary text-xs px-8 py-3 w-full sm:w-auto text-center"
            >
              Continue to Payment →
            </button>
          </div>
        </div>

        {/* Right Column: Order Summary & Items Preview */}
        <div className="sticky top-28 space-y-6">
          <div className="border border-borderIvory bg-white/70 p-6 shadow-[0_2px_12px_rgba(0,0,0,0.02)]">
            <h2 className="font-display text-xl text-ink font-normal pb-3.5 border-b border-borderIvory">
              Order Summary
            </h2>

            {/* Items list preview */}
            <div className="mt-4 divide-y divide-borderIvory/70 max-h-60 overflow-y-auto pr-1">
              {order.items.map((item, idx) => {
                const prod = productsMap[item.productId];
                const productName =
                  prod?.name || (item as any).productName || "Product details unavailable";
                const variant = item.variantKey || (item as any).variant_key;
                const itemImg = prod?.imageUrl;
                const lineTotal =
                  typeof item.lineTotal === "number"
                    ? item.lineTotal
                    : (item.quantity || 1) * (item.unitPrice || 0);

                return (
                  <div key={item.id || idx} className="py-3 flex items-center gap-3 text-xs">
                    {itemImg ? (
                      <img
                        src={itemImg}
                        alt={productName}
                        className="w-12 h-14 object-cover border border-borderIvory bg-[#ECE8E1] shrink-0"
                        onError={(e) => {
                          (e.target as HTMLElement).style.display = "none";
                        }}
                      />
                    ) : (
                      <ProductImagePlaceholder className="w-12 h-14" />
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-ink truncate">{productName}</p>
                      <p className="text-[11px] text-ink/55">
                        {variant ? `Size: ${variant} · ` : ""}Qty: {item.quantity}
                      </p>
                    </div>
                    <div className="text-right font-medium text-ink shrink-0">
                      {money(lineTotal)}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mt-4 pt-3.5 border-t border-borderIvory/80 space-y-2.5 text-xs">
              <div className="flex justify-between items-center text-ink/75">
                <span>Subtotal</span>
                <span className="font-medium text-ink">{money(subtotal)}</span>
              </div>
              <div className="border-t border-borderIvory/80 pt-2.5 flex justify-between items-baseline">
                <span className="text-sm font-semibold text-ink">Total Amount</span>
                <span className="font-sans text-xl font-bold text-ink">{money(order.total)}</span>
              </div>
            </div>

            <div className="mt-5 pt-3.5 border-t border-borderIvory/60 text-[11px] leading-relaxed text-ink/50">
              Safe demonstration mode. No real banking details will ever be asked or stored.
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function getInitials(name: string): string {
  if (!name || !name.trim()) return "C";
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function ProfilePage() {
  const { user, updateUser, becomeSeller, signOut } = useMarketplace();
  const [searchParams] = useSearchParams();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loadingOrders, setLoadingOrders] = useState(true);
  const [activeTab, setActiveTab] = useState<"personal" | "store" | "settings">("personal");

  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState("");
  const [editEmail, setEditEmail] = useState("");
  const [editStoreName, setEditStoreName] = useState("");
  const [editError, setEditError] = useState("");
  const [editSuccess, setEditSuccess] = useState("");

  // Become a Seller Modal & state
  const [becomeSellerOpen, setBecomeSellerOpen] = useState(false);
  const [newStoreName, setNewStoreName] = useState("");
  const [becomeSellerLoading, setBecomeSellerLoading] = useState(false);
  const [becomeSellerError, setBecomeSellerError] = useState("");

  const role: UserRole = user?.role || "buyer";
  const isSeller = role === "seller";

  useEffect(() => {
    if (searchParams.get("action") === "become-seller" && !isSeller) {
      setBecomeSellerOpen(true);
    }
  }, [searchParams, isSeller]);

  useEffect(() => {
    if (user) {
      setEditName(user.name);
      setEditEmail(user.email);
      setEditStoreName(user.storeName || "");
      if (user.role === "seller") {
        setActiveTab("store");
      }

      mockMarketplaceService
        .listOrders(user.email)
        .then(setOrders)
        .catch(() => setOrders([]))
        .finally(() => setLoadingOrders(false));
    }
  }, [user]);

  if (!user) {
    return (
      <EmptyState
        title="Your profile is waiting."
        detail="Sign in to view and manage your account details."
        action="Sign in"
        to="/login?next=%2Faccount%2Fprofile"
      />
    );
  }

  const handleStartEdit = (tab?: "personal" | "store") => {
    if (tab) setActiveTab(tab);
    setEditName(user.name);
    setEditEmail(user.email);
    setEditStoreName(user.storeName || "");
    setEditError("");
    setEditSuccess("");
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setEditName(user.name);
    setEditEmail(user.email);
    setEditStoreName(user.storeName || "");
    setEditError("");
    setIsEditing(false);
  };

  const handleSaveEdit = async (e: FormEvent) => {
    e.preventDefault();
    setEditError("");
    setEditSuccess("");

    if (activeTab === "store") {
      if (!editStoreName.trim()) {
        setEditError("Store / Atelier name is required.");
        return;
      }
      try {
        await updateUser({
          storeName: editStoreName.trim(),
        });
        setIsEditing(false);
        setEditSuccess("Store information has been successfully updated.");
      } catch (err) {
        setEditError(err instanceof Error ? err.message : "Unable to update store information.");
      }
      return;
    }

    if (!editName.trim()) {
      setEditError("Full name cannot be empty.");
      return;
    }

    try {
      await updateUser({
        name: editName.trim(),
      });
      setIsEditing(false);
      setEditSuccess("Your details have been successfully updated.");
    } catch (err) {
      setEditError(err instanceof Error ? err.message : "Unable to update profile details.");
    }
  };

  const handleBecomeSeller = async (e: FormEvent) => {
    e.preventDefault();
    setBecomeSellerError("");
    const cleanName = newStoreName.trim();
    if (!cleanName) {
      setBecomeSellerError("Store / Atelier name is required.");
      return;
    }
    if (cleanName.length < 2) {
      setBecomeSellerError("Store name must be at least 2 characters.");
      return;
    }
    setBecomeSellerLoading(true);
    try {
      await becomeSeller(cleanName);
      setBecomeSellerOpen(false);
      setNewStoreName("");
      setEditSuccess(`Congratulations! Your boutique "${cleanName}" is now ACTIVE. You can now publish collections and fulfill orders.`);
      setActiveTab("store");
    } catch (err) {
      setBecomeSellerError(err instanceof Error ? err.message : "Unable to activate boutique atelier.");
    } finally {
      setBecomeSellerLoading(false);
    }
  };

  // Real boutique products matching seller storeName
  const boutiqueProducts = isSeller && user.storeName
    ? mockProducts.filter(
      (p) => p.designer.toLowerCase() === user.storeName!.toLowerCase(),
    )
    : [];

  return (
    <section className="mx-auto max-w-6xl px-5 sm:px-8 py-10 md:py-16">
      {/* Breadcrumb */}
      <nav aria-label="Breadcrumb" className="mb-6 flex items-center gap-2 text-xs text-ink/50">
        <Link to="/" className="hover:text-ink transition-colors">Home</Link>
        <span>/</span>
        <span className="text-ink font-medium">{isSeller ? "My Boutique" : "My Account"}</span>
      </nav>

      {/* Header Banner */}
      <div className="border-b border-borderIvory pb-8">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
          <div className="flex items-center gap-5">
            <div className="w-16 h-16 rounded-full bg-ink text-paper font-display text-2xl flex items-center justify-center tracking-wider shrink-0 shadow-sm">
              {getInitials(user.name)}
            </div>
            <div>
              <p className="eyebrow tracking-[0.2em] text-ink/65">
                {isSeller ? "ATELIER DASHBOARD" : "CLIENT DASHBOARD"}
              </p>
              <h1 className="mt-1 font-display text-3xl sm:text-4xl text-ink">
                {isSeller ? "My Boutique" : "My Account"}
              </h1>
              <p className="mt-1 text-xs sm:text-sm text-ink/60">
                {isSeller
                  ? "Manage your boutique profile and your Clothify experience."
                  : "Manage your details and your Clothify experience."}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span
              className={`inline-flex items-center px-3.5 py-1.5 rounded-full text-xs font-medium uppercase tracking-wider ${isSeller
                ? "bg-[#E8EDE6] text-[#475240] border border-[#DDD8CE]"
                : "bg-white text-ink border border-borderIvory"
                }`}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-current mr-2" />
              {isSeller ? "Seller Account" : "Buyer Account"}
            </span>

            {!isSeller && (
              <button
                type="button"
                onClick={() => { setBecomeSellerError(""); setBecomeSellerOpen(true); }}
                className="button-primary text-xs px-4 py-1.5 inline-flex items-center gap-1.5 shadow-sm"
              >
                <span>Open Boutique Atelier</span>
                <span className="text-[10px]">✦</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Main Dashboard Layout */}
      <div className="mt-8 grid grid-cols-1 md:grid-cols-12 gap-8 lg:gap-12">
        {/* Sidebar Navigation */}
        <aside className="md:col-span-4 lg:col-span-3">
          <div className="rounded border border-borderIvory bg-white/70 p-4 space-y-1">
            <p className="px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-ink/50">
              Account Menu
            </p>

            {isSeller ? (
              <>
                <button
                  type="button"
                  onClick={() => { setActiveTab("store"); setIsEditing(false); }}
                  className={`w-full text-left px-3 py-2.5 rounded text-xs tracking-wider transition-colors flex items-center justify-between ${activeTab === "store"
                    ? "bg-ink text-paper font-semibold"
                    : "text-ink/80 hover:bg-ink/5"
                    }`}
                >
                  <span>Store Information</span>
                  <span className="text-[10px]">→</span>
                </button>

                <button
                  type="button"
                  onClick={() => { setActiveTab("personal"); setIsEditing(false); }}
                  className={`w-full text-left px-3 py-2.5 rounded text-xs tracking-wider transition-colors flex items-center justify-between ${activeTab === "personal"
                    ? "bg-ink text-paper font-semibold"
                    : "text-ink/80 hover:bg-ink/5"
                    }`}
                >
                  <span>Personal Information</span>
                  <span className="text-[10px]">→</span>
                </button>

                <button
                  type="button"
                  onClick={() => { setActiveTab("settings"); setIsEditing(false); }}
                  className={`w-full text-left px-3 py-2.5 rounded text-xs tracking-wider transition-colors flex items-center justify-between ${activeTab === "settings"
                    ? "bg-ink text-paper font-semibold"
                    : "text-ink/80 hover:bg-ink/5"
                    }`}
                >
                  <span>Account Settings</span>
                  <span className="text-[10px]">→</span>
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => { setActiveTab("personal"); setIsEditing(false); }}
                  className={`w-full text-left px-3 py-2.5 rounded text-xs tracking-wider transition-colors flex items-center justify-between ${activeTab === "personal"
                    ? "bg-ink text-paper font-semibold"
                    : "text-ink/80 hover:bg-ink/5"
                    }`}
                >
                  <span>Personal Information</span>
                  <span className="text-[10px]">→</span>
                </button>

                <button
                  type="button"
                  onClick={() => { setBecomeSellerError(""); setBecomeSellerOpen(true); }}
                  className="w-full text-left px-3 py-2.5 rounded text-xs tracking-wider transition-colors flex items-center justify-between text-ink/90 hover:bg-ink/5 bg-paper/60 border border-borderIvory/70 my-1"
                >
                  <div className="flex items-center gap-1.5">
                    <span className="text-[#8B5E3C] font-semibold">✦</span>
                    <span className="font-medium text-ink">Become a Seller</span>
                  </div>
                  <span className="text-[10px] text-ink/50 bg-white px-1.5 py-0.5 rounded border border-borderIvory">Free</span>
                </button>

                <Link
                  to="/account/orders"
                  className="w-full text-left px-3 py-2.5 rounded text-xs tracking-wider text-ink/80 hover:bg-ink/5 transition-colors flex items-center justify-between"
                >
                  <span>My Orders</span>
                  <span className="text-[10px] bg-paper px-2 py-0.5 rounded border border-borderIvory text-ink/70">
                    {loadingOrders ? "…" : orders.length}
                  </span>
                </Link>

                <div
                  className="w-full text-left px-3 py-2.5 rounded text-xs tracking-wider text-ink/35 flex items-center justify-between cursor-not-allowed"
                  title="Address book is not yet supported in this demo"
                >
                  <span>Addresses</span>
                  <span className="text-[10px] text-ink/35 italic">Inactive</span>
                </div>

                <div
                  className="w-full text-left px-3 py-2.5 rounded text-xs tracking-wider text-ink/35 flex items-center justify-between cursor-not-allowed"
                  title="Wishlist is not yet supported in this demo"
                >
                  <span>Wishlist</span>
                  <span className="text-[10px] text-ink/35 italic">Inactive</span>
                </div>

                <button
                  type="button"
                  onClick={() => { setActiveTab("settings"); setIsEditing(false); }}
                  className={`w-full text-left px-3 py-2.5 rounded text-xs tracking-wider transition-colors flex items-center justify-between ${activeTab === "settings"
                    ? "bg-ink text-paper font-semibold"
                    : "text-ink/80 hover:bg-ink/5"
                    }`}
                >
                  <span>Account Settings</span>
                  <span className="text-[10px]">→</span>
                </button>
              </>
            )}

            <div className="pt-2 border-t border-borderIvory mt-2">
              <button
                type="button"
                onClick={signOut}
                className="w-full text-left px-3 py-2 rounded text-xs text-red-700 hover:bg-red-50 transition-colors"
              >
                Sign Out
              </button>
            </div>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="md:col-span-8 lg:col-span-9 space-y-8">
          {/* Notifications */}
          {editSuccess && (
            <div className="rounded border border-moss/30 bg-[#E8EDE6]/70 p-4 text-xs text-[#384333] flex items-center justify-between">
              <span>✓ {editSuccess}</span>
              <button type="button" onClick={() => setEditSuccess("")} className="text-ink/50 hover:text-ink">✕</button>
            </div>
          )}

          {editError && <ErrorMessage>{editError}</ErrorMessage>}

          {/* Become a Seller callout banner for buyers */}
          {!isSeller && (
            <div className="rounded border border-borderIvory bg-gradient-to-br from-white via-paper to-[#F5F2EB] p-6 sm:p-8 relative overflow-hidden shadow-sm">
              <div className="max-w-xl">
                <p className="eyebrow tracking-[0.2em] text-[#8B5E3C]">CLOTHIFY ATELIER PROGRAM</p>
                <h2 className="mt-1 font-display text-2xl sm:text-3xl text-ink">
                  Present your collections on Clothify
                </h2>
                <p className="mt-2 text-xs sm:text-sm text-ink/70 leading-relaxed">
                  Open a boutique atelier using this single account. Your store is activated immediately with full catalogue and order fulfillment tools — no secondary registration or admin wait time required.
                </p>
                <div className="mt-5 flex items-center gap-4">
                  <button
                    type="button"
                    onClick={() => { setBecomeSellerError(""); setBecomeSellerOpen(true); }}
                    className="button-primary text-xs px-6 py-3"
                  >
                    Open Boutique Atelier (Become a Seller)
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Overview Cards (Real data only!) */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {isSeller ? (
              <>
                <div className="rounded border border-borderIvory bg-white/70 p-5">
                  <p className="eyebrow tracking-[0.16em] text-ink/50 text-[10px]">BOUTIQUE PRODUCTS</p>
                  <p className="mt-2 text-2xl font-display text-ink font-normal">
                    {boutiqueProducts.length > 0 ? `${boutiqueProducts.length} pieces` : "No products yet"}
                  </p>
                  <p className="mt-1 text-xs text-ink/55">Active catalogue listings</p>
                </div>

                <div className="rounded border border-borderIvory bg-white/70 p-5">
                  <p className="eyebrow tracking-[0.16em] text-ink/50 text-[10px]">ORDERS & SALES</p>
                  <p className="mt-2 text-2xl font-display text-ink font-normal">
                    No sales yet
                  </p>
                  <p className="mt-1 text-xs text-ink/55">Real atelier sales activity</p>
                </div>

                <div className="rounded border border-borderIvory bg-white/70 p-5">
                  <p className="eyebrow tracking-[0.16em] text-ink/50 text-[10px]">MEMBERSHIP</p>
                  <p className="mt-2 text-2xl font-display text-ink font-normal">
                    Verified Seller
                  </p>
                  <p className="mt-1 text-xs text-ink/55">Clothify Boutique Partner</p>
                </div>
              </>
            ) : (
              <>
                <div className="rounded border border-borderIvory bg-white/70 p-5">
                  <p className="eyebrow tracking-[0.16em] text-ink/50 text-[10px]">TOTAL ORDERS</p>
                  <p className="mt-2 text-2xl font-display text-ink font-normal">
                    {loadingOrders ? "…" : orders.length}
                  </p>
                  <div className="mt-1 flex items-center justify-between text-xs">
                    <span className="text-ink/55">Placed orders</span>
                    {orders.length > 0 && (
                      <Link to="/account/orders" className="text-ink underline text-[11px]">View all</Link>
                    )}
                  </div>
                </div>

                <div className="rounded border border-borderIvory bg-white/70 p-5">
                  <p className="eyebrow tracking-[0.16em] text-ink/50 text-[10px]">SAVED ADDRESSES</p>
                  <p className="mt-2 text-2xl font-display text-ink font-normal">
                    None saved
                  </p>
                  <p className="mt-1 text-xs text-ink/55">No saved shipping addresses</p>
                </div>

                <div className="rounded border border-borderIvory bg-white/70 p-5">
                  <p className="eyebrow tracking-[0.16em] text-ink/50 text-[10px]">WISHLIST</p>
                  <p className="mt-2 text-2xl font-display text-ink font-normal">
                    Empty
                  </p>
                  <p className="mt-1 text-xs text-ink/55">No saved pieces in wishlist</p>
                </div>
              </>
            )}
          </div>

          {/* Section: Store Information (For Seller) */}
          {isSeller && activeTab === "store" && (
            <div className="rounded border border-borderIvory bg-white/70 p-6 sm:p-8">
              <div className="flex items-center justify-between border-b border-borderIvory pb-4 mb-6">
                <div>
                  <h2 className="font-display text-2xl text-ink">Store Information</h2>
                  <p className="text-xs text-ink/60 mt-0.5">Your luxury atelier presence on Clothify</p>
                </div>
                {!isEditing && (
                  <button
                    type="button"
                    onClick={() => handleStartEdit("store")}
                    className="button-secondary text-xs px-4 py-2"
                  >
                    Edit Store Information
                  </button>
                )}
              </div>

              {isEditing ? (
                <form onSubmit={handleSaveEdit} className="space-y-5" noValidate>
                  <div>
                    <label htmlFor="edit-storename" className="block text-xs font-semibold uppercase tracking-wider text-ink/75">
                      Store / Atelier Name <span className="text-clay">*</span>
                    </label>
                    <input
                      id="edit-storename"
                      type="text"
                      className="field mt-1.5"
                      value={editStoreName}
                      onChange={(e) => setEditStoreName(e.target.value)}
                      placeholder="e.g. Maison Laurent Atelier"
                      required
                    />
                  </div>

                  <div className="pt-2 flex items-center gap-3">
                    <button type="submit" className="button-primary text-xs px-6 py-3">
                      Save Changes
                    </button>
                    <button
                      type="button"
                      onClick={handleCancelEdit}
                      className="button-secondary text-xs px-6 py-3"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 text-sm">
                  <div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-ink/50">Store / Atelier Name</span>
                    <p className="mt-1.5 font-medium text-ink text-base">
                      {user.storeName || "Not configured"}
                    </p>
                  </div>
                  <div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-ink/50">Partner Category</span>
                    <p className="mt-1.5 text-ink">Boutique Atelier</p>
                  </div>
                  <div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-ink/50">Catalogue Status</span>
                    <p className="mt-1.5 text-ink">
                      {boutiqueProducts.length > 0 ? `${boutiqueProducts.length} pieces active` : "No products yet"}
                    </p>
                  </div>
                  <div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-ink/50">Atelier ID</span>
                    <p className="mt-1.5 text-xs text-ink/60 font-mono">SELLER-{user.email.split("@")[0].toUpperCase()}</p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Section: Personal Information */}
          {activeTab === "personal" && (
            <div className="rounded border border-borderIvory bg-white/70 p-6 sm:p-8">
              <div className="flex items-center justify-between border-b border-borderIvory pb-4 mb-6">
                <div>
                  <h2 className="font-display text-2xl text-ink">Personal Information</h2>
                  <p className="text-xs text-ink/60 mt-0.5">Your profile and contact credentials</p>
                </div>
                {!isEditing && (
                  <button
                    type="button"
                    onClick={() => handleStartEdit("personal")}
                    className="button-secondary text-xs px-4 py-2"
                  >
                    Edit Details
                  </button>
                )}
              </div>

              {isEditing ? (
                <form onSubmit={handleSaveEdit} className="space-y-5" noValidate>
                  <div>
                    <label htmlFor="edit-name" className="block text-xs font-semibold uppercase tracking-wider text-ink/75">
                      Full Name <span className="text-clay">*</span>
                    </label>
                    <input
                      id="edit-name"
                      type="text"
                      className="field mt-1.5"
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      required
                    />
                  </div>

                  <div>
                    <label htmlFor="edit-email" className="block text-xs font-semibold uppercase tracking-wider text-ink/75">
                      Email Address <span className="text-clay">*</span>
                    </label>
                    <input
                      id="edit-email"
                      type="email"
                      className="field mt-1.5"
                      value={editEmail}
                      onChange={(e) => setEditEmail(e.target.value)}
                      required
                    />
                  </div>

                  <div className="pt-2 flex items-center gap-3">
                    <button type="submit" className="button-primary text-xs px-6 py-3">
                      Save Changes
                    </button>
                    <button
                      type="button"
                      onClick={handleCancelEdit}
                      className="button-secondary text-xs px-6 py-3"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 text-sm">
                  <div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-ink/50">Full Name</span>
                    <p className="mt-1.5 font-medium text-ink text-base">{user.name}</p>
                  </div>
                  <div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-ink/50">Email Address</span>
                    <p className="mt-1.5 text-ink">{user.email}</p>
                  </div>
                  <div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-ink/50">Account Role</span>
                    <p className="mt-1.5 text-ink capitalize">{role}</p>
                  </div>
                  <div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-ink/50">Registration Status</span>
                    <p className="mt-1.5 text-ink">Active Client Profile</p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Section: Account Settings */}
          {activeTab === "settings" && (
            <div className="rounded border border-borderIvory bg-white/70 p-6 sm:p-8 space-y-6">
              <div className="border-b border-borderIvory pb-4">
                <h2 className="font-display text-2xl text-ink">Account Settings</h2>
                <p className="text-xs text-ink/60 mt-0.5">Preferences and local session management</p>
              </div>

              <div className="space-y-4 text-xs text-ink/75">
                <div className="p-4 rounded border border-borderIvory bg-paper">
                  <p className="font-semibold text-ink text-sm">Demo Session Info</p>
                  <p className="mt-1 leading-relaxed text-ink/65">
                    This account is running in client demo mode. Profiles and updates are maintained in this browser session.
                  </p>
                </div>

                <div className="pt-4 flex items-center justify-between border-t border-borderIvory">
                  <div>
                    <p className="font-semibold text-ink text-sm">End Active Session</p>
                    <p className="text-ink/60">Sign out of this profile on Clothify</p>
                  </div>
                  <button
                    type="button"
                    onClick={signOut}
                    className="button-secondary text-xs text-red-700 hover:border-red-400"
                  >
                    Sign Out
                  </button>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Become a Seller Modal Dialog */}
      {becomeSellerOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/40 backdrop-blur-sm animate-fadeIn">
          <div className="bg-paper border border-borderIvory rounded-lg shadow-xl max-w-md w-full p-6 sm:p-8 space-y-6 animate-scaleUp">
            <div className="flex items-start justify-between">
              <div>
                <p className="eyebrow tracking-[0.2em] text-[#8B5E3C] text-[10px]">INSTANT ACTIVATION</p>
                <h3 className="mt-1 font-display text-2xl text-ink">Open Boutique Atelier</h3>
                <p className="text-xs text-ink/65 mt-1 leading-relaxed">
                  Activate your atelier to publish designs and manage sales. Your buyer history and bag remain intact.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setBecomeSellerOpen(false)}
                className="text-ink/40 hover:text-ink text-sm p-1"
                aria-label="Close dialog"
              >
                ✕
              </button>
            </div>

            {becomeSellerError && <ErrorMessage>{becomeSellerError}</ErrorMessage>}

            <form onSubmit={handleBecomeSeller} className="space-y-5" noValidate>
              <div>
                <label htmlFor="new-storename" className="block text-xs font-semibold uppercase tracking-wider text-ink/75">
                  Store / Atelier Name <span className="text-clay">*</span>
                </label>
                <input
                  id="new-storename"
                  type="text"
                  autoComplete="organization"
                  placeholder="e.g. Maison Laurent Atelier"
                  className="field mt-1.5"
                  value={newStoreName}
                  onChange={(e) => setNewStoreName(e.target.value)}
                  disabled={becomeSellerLoading}
                  required
                  autoFocus
                />
                <p className="mt-1.5 text-[11px] text-ink/50">
                  This name will appear on your product pieces and boutique profile.
                </p>
              </div>

              <div className="pt-2 flex items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setBecomeSellerOpen(false)}
                  className="button-secondary text-xs px-5 py-2.5"
                  disabled={becomeSellerLoading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="button-primary text-xs px-6 py-2.5"
                  disabled={becomeSellerLoading}
                >
                  {becomeSellerLoading ? "Activating..." : "Open Store (Activate)"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}

export function SellerProductsPage() {
  const { user } = useMarketplace();

  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  // Tabs: Products vs Fulfillment
  const [activeTab, setActiveTab] = useState<"products" | "fulfillment">("products");
  const [sellerOrders, setSellerOrders] = useState<any[]>([]);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [ordersError, setOrdersError] = useState("");

  // Shipment Update Modal State
  const [selectedOrder, setSelectedOrder] = useState<any | null>(null);
  const [shipmentModalOpen, setShipmentModalOpen] = useState(false);
  const [carrierName, setCarrierName] = useState("");
  const [trackingNumber, setTrackingNumber] = useState("");
  const [statusVal, setStatusVal] = useState("DISPATCHED");
  const [updatingShipment, setUpdatingShipment] = useState(false);
  const [shipmentError, setShipmentError] = useState("");

  // Create & Edit form modal state
  const [formOpen, setFormOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);

  // Form input states
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState("");
  const [category, setCategory] = useState<string>(MARKETPLACE_CATEGORIES[0]);
  const [color, setColor] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [hasVariants, setHasVariants] = useState(true);
  const [simpleStock, setSimpleStock] = useState("10");
  const [variantList, setVariantList] = useState<StockItemInput[]>([
    { variant_key: "S", available_quantity: 10 },
    { variant_key: "M", available_quantity: 15 },
  ]);

  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  const categories = MARKETPLACE_CATEGORIES;

  const loadProducts = () => {
    setLoading(true);
    setError("");
    productService
      .listSellerProducts()
      .then((items) => {
        setProducts(items);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Could not load atelier pieces.");
      })
      .finally(() => setLoading(false));
  };

  const loadSellerOrders = () => {
    setOrdersLoading(true);
    setOrdersError("");
    orderService
      .getSellerOrders()
      .then((items) => {
        setSellerOrders(items);
      })
      .catch((err: unknown) => {
        setOrdersError(err instanceof Error ? err.message : "Could not load studio orders.");
      })
      .finally(() => setOrdersLoading(false));
  };

  useEffect(() => {
    if (user && user.role === "seller") {
      if (activeTab === "products") {
        loadProducts();
      } else {
        loadSellerOrders();
      }
    } else {
      setLoading(false);
    }
  }, [user, activeTab]);

  const openShipmentModal = (ord: any) => {
    setSelectedOrder(ord);
    const existingShp = ord.shipment;
    setCarrierName(existingShp?.carrier_name || "DHL Express");
    setTrackingNumber(existingShp?.tracking_number || "");
    setStatusVal(existingShp?.status === "DELIVERED" ? "DELIVERED" : (existingShp?.status || "DISPATCHED"));
    setShipmentError("");
    setShipmentModalOpen(true);
  };

  const handleUpdateShipmentSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedOrder) return;
    setUpdatingShipment(true);
    setShipmentError("");
    try {
      await orderService.updateSellerShipment(selectedOrder.id, {
        carrier_name: carrierName.trim() || undefined,
        tracking_number: trackingNumber.trim() || undefined,
        status: statusVal,
      });
      setShipmentModalOpen(false);
      setNotice(`Shipment for Order #${selectedOrder.id.slice(0, 8)} updated to ${statusVal}.`);
      loadSellerOrders();
    } catch (err) {
      setShipmentError(err instanceof Error ? err.message : "Failed to update shipment.");
    } finally {
      setUpdatingShipment(false);
    }
  };

  function openCreateModal() {
    setEditingProduct(null);
    setName("");
    setDescription("");
    setPrice("");
    setCategory(MARKETPLACE_CATEGORIES[0]);
    setColor("");
    setImageUrl("");
    setIsActive(true);
    setHasVariants(true);
    setSimpleStock("10");
    setVariantList([
      { variant_key: "S", available_quantity: 10 },
      { variant_key: "M", available_quantity: 15 },
    ]);
    setFormError("");
    setFormOpen(true);
  }

  function openEditModal(prod: Product) {
    setEditingProduct(prod);
    setName(prod.name);
    setDescription(prod.description);
    setPrice(String(prod.price));
    setCategory(prod.category || MARKETPLACE_CATEGORIES[0]);
    setColor(prod.color || "");
    setImageUrl(prod.imageUrl || "");
    setIsActive(prod.isActive ?? true);
    if (prod.variants && prod.variants.length > 0) {
      setHasVariants(true);
      setVariantList(
        prod.variants.map((v) => ({
          variant_key: v.variantKey,
          available_quantity: v.availableQuantity,
        })),
      );
      setSimpleStock(String(prod.availableStock));
    } else {
      setHasVariants(false);
      setSimpleStock(String(prod.availableStock));
      setVariantList([
        { variant_key: "S", available_quantity: 10 },
        { variant_key: "M", available_quantity: 15 },
      ]);
    }
    setFormError("");
    setFormOpen(true);
  }

  function handleAddVariantRow() {
    setVariantList([...variantList, { variant_key: "", available_quantity: 5 }]);
  }

  function handleRemoveVariantRow(index: number) {
    setVariantList(variantList.filter((_, idx) => idx !== index));
  }

  function handleVariantChange(index: number, field: "key" | "qty", val: string) {
    const updated = [...variantList];
    if (field === "key") {
      updated[index].variant_key = val;
    } else {
      updated[index].available_quantity = Math.max(0, parseInt(val || "0", 10));
    }
    setVariantList(updated);
  }

  async function handleToggleStatus(prod: Product) {
    const nextStatus = !prod.isActive;
    try {
      await productService.toggleProductStatus(prod.id, nextStatus);
      setNotice(`"${prod.name}" is now ${nextStatus ? "active and live on catalog" : "hidden/inactive"}.`);
      loadProducts();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to toggle piece status.");
    }
  }

  async function handleSubmitProduct(e: FormEvent) {
    e.preventDefault();
    setFormError("");

    if (!name.trim()) {
      setFormError("Piece name is required.");
      return;
    }
    if (!description.trim()) {
      setFormError("Piece description is required.");
      return;
    }
    const numPrice = parseFloat(price);
    if (isNaN(numPrice) || numPrice <= 0) {
      setFormError("Please enter a valid price greater than zero.");
      return;
    }
    if (!category.trim()) {
      setFormError("Category is required.");
      return;
    }

    if (imageUrl.trim()) {
      try {
        const parsed = new URL(imageUrl.trim());
        if (!parsed.protocol.startsWith("http")) {
          setFormError("Image URL must use http:// or https:// protocol.");
          return;
        }
      } catch {
        setFormError("Please enter a valid Image URL (e.g., https://images.unsplash.com/...).");
        return;
      }
    }

    let payloadVariants: StockItemInput[] | undefined = undefined;
    let payloadStock = 0;

    if (hasVariants) {
      if (variantList.length === 0) {
        setFormError("Please define at least one variant or toggle to simple stock.");
        return;
      }
      const cleanedVariants: StockItemInput[] = [];
      const seenKeys = new Set<string>();

      for (const v of variantList) {
        const k = v.variant_key.trim().toUpperCase();
        if (!k) {
          setFormError("Each variant requires a size / key (e.g. S, M, L).");
          return;
        }
        if (seenKeys.has(k)) {
          setFormError(`Duplicate variant key "${k}". Each variant must be unique.`);
          return;
        }
        seenKeys.add(k);
        cleanedVariants.push({
          variant_key: k,
          available_quantity: v.available_quantity,
        });
      }
      payloadVariants = cleanedVariants;
      payloadStock = cleanedVariants.reduce((sum, v) => sum + v.available_quantity, 0);
    } else {
      payloadStock = Math.max(0, parseInt(simpleStock || "0", 10));
    }

    setSubmitting(true);
    try {
      if (editingProduct) {
        const updatePayload: ProductUpdateInput = {
          name: name.trim(),
          description: description.trim(),
          price: numPrice,
          category: category.trim(),
          color: color.trim() || undefined,
          image_url: imageUrl.trim() || undefined,
          is_active: isActive,
          variants: payloadVariants,
          stock_quantity: payloadVariants ? undefined : payloadStock,
        };
        await productService.updateProduct(editingProduct.id, updatePayload);
        setNotice(`Successfully updated "${name.trim()}".`);
      } else {
        const createPayload: ProductCreateInput = {
          name: name.trim(),
          description: description.trim(),
          price: numPrice,
          category: category.trim(),
          color: color.trim() || undefined,
          image_url: imageUrl.trim() || undefined,
          variants: payloadVariants,
          stock_quantity: payloadStock,
        };
        await productService.createProduct(createPayload);
        setNotice(`Successfully added "${name.trim()}" to your collection.`);
      }

      setFormOpen(false);
      loadProducts();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to save piece.");
    } finally {
      setSubmitting(false);
    }
  }

  // Not logged in guard
  if (!user) {
    return (
      <div className="mx-auto max-w-4xl px-5 sm:px-8 py-20 text-center">
        <p className="eyebrow">Seller Verification Required</p>
        <h1 className="mt-3 font-display text-4xl text-ink">Sign in to Access Seller Studio</h1>
        <p className="mt-4 text-sm text-ink/65 max-w-md mx-auto">
          Manage your luxury catalog, update inventory, and present new seasonal creations.
        </p>
        <Link to="/login" className="button-primary mt-8 inline-flex">
          Sign In to Atelier
        </Link>
      </div>
    );
  }

  // Role guard (Buyer trying to access seller studio)
  if (user.role !== "seller") {
    return (
      <div className="mx-auto max-w-4xl px-5 sm:px-8 py-20 text-center">
        <p className="eyebrow">Restricted Area</p>
        <h1 className="mt-3 font-display text-4xl text-ink">Seller Account Required</h1>
        <p className="mt-4 text-sm text-ink/65 max-w-md mx-auto">
          Your current account is registered as a Buyer. To publish and manage collections, open your boutique atelier from your Profile page — no secondary account needed.
        </p>
        <div className="mt-8 flex justify-center gap-4">
          <Link to="/account/profile?action=become-seller" className="button-primary">
            Open Boutique Atelier (Become a Seller)
          </Link>
          <Link to="/products" className="button-secondary">
            Explore Collection
          </Link>
        </div>
      </div>
    );
  }

  return (
    <section className="mx-auto max-w-7xl px-5 sm:px-8 py-10 md:py-16 space-y-10">
      {/* Studio Header */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-6 border-b border-borderIvory pb-8">
        <div>
          <p className="eyebrow">Clothify · Atelier Management</p>
          <h1 className="mt-2 font-display text-4xl sm:text-5xl text-ink">Seller Studio</h1>
          <p className="mt-2 text-sm text-ink/65">
            Store: <strong className="text-ink font-medium">{user.storeName || user.name}</strong> ·{" "}
            {products.length} {products.length === 1 ? "piece" : "pieces"} published
          </p>
        </div>
        <button
          type="button"
          onClick={openCreateModal}
          className="button-primary flex items-center justify-center gap-2 self-start sm:self-auto"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
          </svg>
          Add New Piece
        </button>
      </div>

      {/* Studio Navigation Tabs */}
      <div className="flex border-b border-borderIvory gap-8 text-sm">
        <button
          type="button"
          onClick={() => setActiveTab("products")}
          className={`pb-3 font-medium transition-colors border-b-2 ${
            activeTab === "products"
              ? "border-ink text-ink font-semibold"
              : "border-transparent text-ink/50 hover:text-ink"
          }`}
        >
          Inventory & Pieces ({products.length})
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("fulfillment")}
          className={`pb-3 font-medium transition-colors border-b-2 ${
            activeTab === "fulfillment"
              ? "border-ink text-ink font-semibold"
              : "border-transparent text-ink/50 hover:text-ink"
          }`}
        >
          Orders & Fulfillment
        </button>
      </div>

      {/* Notifications */}
      {notice && (
        <div className="rounded border border-moss/30 bg-moss/10 px-4 py-3 text-sm text-moss flex items-center justify-between">
          <span>{notice}</span>
          <button type="button" onClick={() => setNotice("")} className="text-xs uppercase font-medium hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {activeTab === "fulfillment" ? (
        <div className="space-y-6">
          {ordersError && (
            <div>
              <ErrorMessage>{ordersError}</ErrorMessage>
              <button type="button" onClick={loadSellerOrders} className="button-secondary mt-3 text-xs">
                Retry Loading Orders
              </button>
            </div>
          )}

          {ordersLoading ? (
            <Loading label="Retrieving incoming orders…" />
          ) : (() => {
            const activeOrders = (sellerOrders || []).filter((ord: any) => ord.status !== "CANCELLED");
            return activeOrders.length === 0 ? (
              <div className="py-20 text-center border border-borderIvory bg-paper/60">
                <p className="eyebrow">Studio Orders</p>
                <h2 className="mt-3 font-display text-3xl text-ink">No orders yet</h2>
                <p className="mt-3 text-sm text-ink/60 max-w-md mx-auto">
                  Orders containing pieces from your atelier will appear here for fulfillment and shipment updates.
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {activeOrders.map((ord: any) => (
                <div key={ord.id} className="border border-borderIvory bg-paper p-5 sm:p-6 shadow-[0_2px_12px_rgba(0,0,0,0.02)] space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-borderIvory/70 gap-2">
                    <div>
                      <span className="eyebrow">Order #{ord.id.slice(0, 8)}</span>
                      <p className="text-xs text-ink/60 mt-0.5">{formatOrderDate(ord.created_at)}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="px-2.5 py-1 text-[10px] font-medium uppercase tracking-wider rounded border border-borderIvory bg-[#F2EFE8] text-ink">
                        Order: {ord.status}
                      </span>
                      <span className="px-2.5 py-1 text-[10px] font-medium uppercase tracking-wider rounded border border-goldIvory bg-goldIvory/30 text-ink">
                        Shipment: {ord.shipment?.status || "PREPARING"}
                      </span>
                    </div>
                  </div>

                  {/* Masked Items belonging to this seller */}
                  <div>
                    <h4 className="text-xs uppercase font-medium tracking-wider text-ink/60 mb-2">Pieces Ordered</h4>
                    <div className="divide-y divide-borderIvory/40 border border-borderIvory/50 bg-[#FBF9F5]">
                      {ord.items.map((it: any) => (
                        <div key={it.id} className="p-3 flex justify-between items-center text-xs">
                          <div>
                            <span className="font-medium text-ink">{it.product_name || `Product #${it.product_id.slice(0, 8)}`}</span>
                            <span className="text-ink/50 ml-2">Size: {it.variant_key}</span>
                          </div>
                          <div className="text-right">
                            <span className="text-ink/60">{it.quantity} × {money(it.unit_price)}</span>
                            <span className="font-medium text-ink ml-3">{money(it.quantity * it.unit_price)}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Shipment Details & Action */}
                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center pt-3 border-t border-borderIvory/50 gap-4 text-xs">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <span className="text-ink/50 uppercase tracking-wider block text-[10px]">Carrier</span>
                        <span className="font-medium text-ink mt-0.5 block">{ord.shipment?.carrier_name || "Standard Delivery"}</span>
                      </div>
                      <div>
                        <span className="text-ink/50 uppercase tracking-wider block text-[10px]">Tracking Number</span>
                        <span className="font-mono font-medium text-ink mt-0.5 block">{ord.shipment?.tracking_number || "Not assigned"}</span>
                      </div>
                    </div>

                    {ord.shipment?.status !== "DELIVERED" ? (
                      <button
                        type="button"
                        onClick={() => openShipmentModal(ord)}
                        className="button-secondary text-xs self-end sm:self-auto"
                      >
                        Update Shipment
                      </button>
                    ) : (
                      <span className="text-xs text-green-700 font-medium py-1 px-2 border border-green-200 bg-green-50 rounded">
                        Delivered
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          );
        })()}
        </div>
      ) : (
        <>
          {error && (
            <div>
              <ErrorMessage>{error}</ErrorMessage>
              <button type="button" onClick={loadProducts} className="button-secondary mt-3 text-xs">
                Retry Loading
              </button>
            </div>
          )}

      {/* Product List */}
      {loading ? (
        <Loading label="Retrieving your studio collection…" />
      ) : products.length === 0 ? (
        <div className="py-20 text-center border border-borderIvory bg-paper/60">
          <p className="eyebrow">Studio Inventory</p>
          <h2 className="mt-3 font-display text-3xl text-ink">No pieces listed yet</h2>
          <p className="mt-3 text-sm text-ink/60 max-w-md mx-auto">
            Ready to present your craftsmanship to discerning buyers? Create your first piece now.
          </p>
          <button type="button" onClick={openCreateModal} className="button-primary mt-8">
            Add Your First Piece
          </button>
        </div>
      ) : (
        <div className="overflow-x-auto border border-borderIvory bg-paper">
          <table className="w-full min-w-[640px] text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-borderIvory bg-[#F2EFE8] uppercase tracking-[0.14em] text-ink/65 font-medium">
                <th className="py-4 px-4 sm:px-6">Piece</th>
                <th className="py-4 px-4">Category</th>
                <th className="py-4 px-4">Price</th>
                <th className="py-4 px-4">Stock & Variants</th>
                <th className="py-4 px-4">Status</th>
                <th className="py-4 px-4 sm:px-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-borderIvory">
              {products.map((prod) => (
                <tr key={prod.id} className="hover:bg-[#F8F6F1] transition">
                  {/* Image & Title */}
                  <td className="py-4 px-4 sm:px-6">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-14 bg-[#ECE8E1] shrink-0 overflow-hidden relative">
                        {prod.imageUrl ? (
                          <img
                            src={prod.imageUrl}
                            alt={prod.name}
                            className="w-full h-full object-cover"
                            onError={(e) => {
                              (e.target as HTMLElement).style.display = "none";
                            }}
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-[9px] text-ink/40">
                            No Img
                          </div>
                        )}
                      </div>
                      <div>
                        <Link
                          to={`/products/${prod.id}`}
                          className="font-medium text-ink hover:underline text-sm line-clamp-1"
                        >
                          {prod.name}
                        </Link>
                        {prod.color && (
                          <span className="text-[11px] text-ink/50 capitalize">
                            Color: {prod.color}
                          </span>
                        )}
                      </div>
                    </div>
                  </td>

                  {/* Category */}
                  <td className="py-4 px-4 text-ink/80 capitalize">{prod.category}</td>

                  {/* Price */}
                  <td className="py-4 px-4 font-medium text-ink">{money(prod.price)}</td>

                  {/* Stock & Variants */}
                  <td className="py-4 px-4">
                    {prod.variants && prod.variants.length > 0 ? (
                      <div>
                        <span className="font-semibold text-ink">{prod.availableStock} total</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {prod.variants.map((v) => (
                            <span
                              key={v.variantKey}
                              className={`text-[10px] px-1.5 py-0.5 rounded border ${v.availableQuantity > 0
                                ? "border-borderIvory bg-paper text-ink/75"
                                : "border-red-200 bg-red-50 text-red-600 line-through"
                                }`}
                            >
                              {v.variantKey}: {v.availableQuantity}
                            </span>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <span className="text-ink font-medium">{prod.availableStock} available</span>
                    )}
                  </td>

                  {/* Status */}
                  <td className="py-4 px-4">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-wider rounded-full ${prod.isActive
                        ? "bg-green-50 text-green-800 border border-green-200"
                        : "bg-ink/10 text-ink/60 border border-borderIvory"
                        }`}
                    >
                      {prod.isActive ? "Live" : "Inactive"}
                    </span>
                  </td>

                  {/* Actions */}
                  <td className="py-4 px-4 sm:px-6 text-right space-x-2">
                    <button
                      type="button"
                      onClick={() => openEditModal(prod)}
                      className="px-2.5 py-1 text-xs border border-borderIvory hover:border-ink transition font-medium"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => handleToggleStatus(prod)}
                      className={`px-2.5 py-1 text-xs border transition font-medium ${prod.isActive
                        ? "border-red-200 text-red-700 hover:bg-red-50"
                        : "border-green-200 text-green-700 hover:bg-green-50"
                        }`}
                    >
                      {prod.isActive ? "Deactivate" : "Activate"}
                    </button>
                    <Link
                      to={`/products/${prod.id}`}
                      className="inline-block px-2 py-1 text-xs text-ink/60 hover:text-ink transition underline"
                    >
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )}

      {/* Shipment Update Modal */}
      {shipmentModalOpen && selectedOrder && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
          <div className="relative w-full max-w-md bg-paper border border-borderIvory p-6 sm:p-8 shadow-2xl">
            <div className="flex items-center justify-between border-b border-borderIvory pb-3 mb-4">
              <div>
                <p className="eyebrow">Order Fulfillment</p>
                <h3 className="font-display text-xl text-ink">Update Shipment</h3>
              </div>
              <button
                type="button"
                onClick={() => setShipmentModalOpen(false)}
                className="text-ink/50 hover:text-ink text-xl leading-none"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-ink/65 mb-4">
              Order #{selectedOrder.id.slice(0, 8)} · Buyer order contains {selectedOrder.items.length} of your pieces
            </p>

            {shipmentError && (
              <div className="mb-4">
                <ErrorMessage>{shipmentError}</ErrorMessage>
              </div>
            )}

            <form onSubmit={handleUpdateShipmentSubmit} className="space-y-4">
              <div>
                <label className="block text-xs uppercase tracking-wider font-medium text-ink mb-1">
                  Shipment Status
                </label>
                <select
                  value={statusVal}
                  onChange={(e) => setStatusVal(e.target.value)}
                  className="field w-full text-xs"
                >
                  <option value="PREPARING">PREPARING (In Atelier)</option>
                  <option value="DISPATCHED">DISPATCHED (Handed to Carrier)</option>
                  <option value="DELIVERED">DELIVERED (Final Arrival)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs uppercase tracking-wider font-medium text-ink mb-1">
                  Carrier Name
                </label>
                <input
                  type="text"
                  placeholder="e.g. DHL Express, FedEx"
                  value={carrierName}
                  onChange={(e) => setCarrierName(e.target.value)}
                  className="field w-full text-xs"
                  required={statusVal === "DISPATCHED"}
                />
              </div>

              <div>
                <label className="block text-xs uppercase tracking-wider font-medium text-ink mb-1">
                  Tracking Number
                </label>
                <input
                  type="text"
                  placeholder="e.g. TRK-12345678"
                  value={trackingNumber}
                  onChange={(e) => setTrackingNumber(e.target.value)}
                  className="field w-full text-xs font-mono"
                  required={statusVal === "DISPATCHED"}
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-borderIvory">
                <button
                  type="button"
                  onClick={() => setShipmentModalOpen(false)}
                  disabled={updatingShipment}
                  className="button-secondary text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updatingShipment}
                  className="button-primary text-xs"
                >
                  {updatingShipment ? "Saving…" : "Save Shipment"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal / Slide-over Dialog for Create & Edit */}
      {formOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-3 sm:p-4 backdrop-blur-sm overflow-y-auto">
          <div className="relative w-full max-w-2xl bg-paper border border-borderIvory p-5 sm:p-8 my-6 sm:my-8 shadow-2xl max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-borderIvory pb-4 mb-6">
              <div>
                <p className="eyebrow">{editingProduct ? "Revise Collection Piece" : "New Creation"}</p>
                <h2 className="font-display text-2xl text-ink">
                  {editingProduct ? `Edit "${editingProduct.name}"` : "Publish New Piece"}
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setFormOpen(false)}
                className="text-ink/50 hover:text-ink text-xl font-light p-1"
                aria-label="Close modal"
              >
                ✕
              </button>
            </div>

            {formError && (
              <div className="mb-6">
                <ErrorMessage>{formError}</ErrorMessage>
              </div>
            )}

            <form onSubmit={handleSubmitProduct} className="space-y-6">
              {/* Name & Category */}
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="prod-name" className="block text-xs uppercase tracking-wider font-medium text-ink mb-1.5">
                    Piece Name *
                  </label>
                  <input
                    id="prod-name"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Tailored Linen Blazer"
                    className="field w-full"
                  />
                </div>
                <div>
                  <label htmlFor="prod-cat" className="block text-xs uppercase tracking-wider font-medium text-ink mb-1.5">
                    Category *
                  </label>
                  <select
                    id="prod-cat"
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="field w-full bg-paper"
                  >
                    {categories.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Price & Color */}
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="prod-price" className="block text-xs uppercase tracking-wider font-medium text-ink mb-1.5">
                    Price (USD $) *
                  </label>
                  <input
                    id="prod-price"
                    type="number"
                    step="0.01"
                    min="0.01"
                    required
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    placeholder="120.00"
                    className="field w-full"
                  />
                </div>
                <div>
                  <label htmlFor="prod-color" className="block text-xs uppercase tracking-wider font-medium text-ink mb-1.5">
                    Color (Optional)
                  </label>
                  <input
                    id="prod-color"
                    value={color}
                    onChange={(e) => setColor(e.target.value)}
                    placeholder="e.g. Ivory, Midnight, Camel"
                    className="field w-full"
                  />
                </div>
              </div>

              {/* Description */}
              <div>
                <label htmlFor="prod-desc" className="block text-xs uppercase tracking-wider font-medium text-ink mb-1.5">
                  Description *
                </label>
                <textarea
                  id="prod-desc"
                  required
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Describe the silhouette, fabric composition, and artisanal craftsmanship..."
                  className="field w-full resize-none"
                />
              </div>

              {/* Image URL */}
              <div>
                <label htmlFor="prod-img" className="block text-xs uppercase tracking-wider font-medium text-ink mb-1.5">
                  Image URL (Optional)
                </label>
                <input
                  id="prod-img"
                  type="url"
                  value={imageUrl}
                  onChange={(e) => setImageUrl(e.target.value)}
                  placeholder="https://images.unsplash.com/photo-..."
                  className="field w-full"
                />
                <p className="mt-1 text-[11px] text-ink/50">
                  Provide a direct public image link. If left blank or invalid, a luxury fallback will be displayed.
                </p>
                {imageUrl && (
                  <div className="mt-2 w-20 h-24 bg-[#ECE8E1] overflow-hidden border border-borderIvory">
                    <img
                      src={imageUrl}
                      alt="Preview"
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        (e.target as HTMLElement).style.display = "none";
                      }}
                    />
                  </div>
                )}
              </div>

              {/* Stock and Variants Management */}
              <div className="border border-borderIvory p-4 bg-[#FBF9F5] rounded">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
                  <div>
                    <h3 className="font-semibold text-xs uppercase tracking-wider text-ink">
                      Inventory Configuration
                    </h3>
                    <p className="text-[11px] text-ink/60">
                      Manage sizes / variants (stocks table) or simple stock quantity
                    </p>
                  </div>
                  <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-ink shrink-0">
                    <input
                      type="checkbox"
                      checked={hasVariants}
                      onChange={(e) => setHasVariants(e.target.checked)}
                      className="rounded border-borderIvory text-ink focus:ring-ink"
                    />
                    Enable Variants
                  </label>
                </div>

                {hasVariants ? (
                  <div className="space-y-3">
                    <div className="space-y-2">
                      {variantList.map((row, idx) => (
                        <div key={idx} className="flex items-center gap-2">
                          <input
                            type="text"
                            placeholder="Size / Key (e.g. S, M, L)"
                            value={row.variant_key}
                            onChange={(e) => handleVariantChange(idx, "key", e.target.value)}
                            className="field flex-1 min-w-[100px] text-xs py-1.5"
                          />
                          <input
                            type="number"
                            min="0"
                            placeholder="Qty"
                            value={row.available_quantity}
                            onChange={(e) => handleVariantChange(idx, "qty", e.target.value)}
                            className="field w-20 sm:w-24 text-xs py-1.5 shrink-0"
                          />
                          {variantList.length > 1 && (
                            <button
                              type="button"
                              onClick={() => handleRemoveVariantRow(idx)}
                              className="text-red-700 hover:text-red-900 text-xs px-2 py-1 shrink-0"
                              aria-label="Remove variant"
                            >
                              ✕
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                    <div className="flex items-center justify-between pt-2">
                      <button
                        type="button"
                        onClick={handleAddVariantRow}
                        className="text-xs uppercase font-medium tracking-wider text-ink underline"
                      >
                        + Add Size / Variant
                      </button>
                      <span className="text-xs text-ink/65 font-medium">
                        Total Stock: {variantList.reduce((sum, v) => sum + (v.available_quantity || 0), 0)}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div>
                    <label htmlFor="simple-stock" className="block text-xs uppercase tracking-wider font-medium text-ink mb-1">
                      Total Available Stock
                    </label>
                    <input
                      id="simple-stock"
                      type="number"
                      min="0"
                      value={simpleStock}
                      onChange={(e) => setSimpleStock(e.target.value)}
                      className="field w-36 text-xs"
                    />
                  </div>
                )}
              </div>

              {/* Active Toggle (when editing) */}
              {editingProduct && (
                <div className="flex items-center gap-2">
                  <input
                    id="is-active"
                    type="checkbox"
                    checked={isActive}
                    onChange={(e) => setIsActive(e.target.checked)}
                    className="rounded border-borderIvory text-ink focus:ring-ink"
                  />
                  <label htmlFor="is-active" className="text-xs font-medium text-ink cursor-pointer">
                    Live on Public Catalog (Active)
                  </label>
                </div>
              )}

              {/* Submit / Cancel Buttons */}
              <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 border-t border-borderIvory pt-5">
                <button
                  type="button"
                  onClick={() => setFormOpen(false)}
                  disabled={submitting}
                  className="button-secondary text-xs w-full sm:w-auto text-center"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="button-primary text-xs min-w-[7rem] w-full sm:w-auto text-center"
                >
                  {submitting ? "Saving Piece…" : editingProduct ? "Save Changes" : "Publish Piece"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}

export function NotFoundPage() {
  return <EmptyState title="This page isn't in the collection." detail="The link may be out of date, or the address may have a typo." action="Back to home" to="/" />;
}

export function MarketplaceProductCount() {
  return <span>{mockProducts.length} pieces</span>;
}
