import {
  MARKETPLACE_CATEGORIES,
  type Product,
  type ProductCreateInput,
  type ProductFilter,
  type ProductUpdateInput,
  type ProductVariant,
  type StockCheckResponse,
} from "../types/marketplace";
import { authService } from "./authService";
import { apiUrl } from "./apiClient";

export const DEFAULT_FALLBACK_IMAGE =
  "https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=1000&q=85";

export function mapApiProduct(item: any): Product {
  const variants: ProductVariant[] = Array.isArray(item.variants)
    ? item.variants.map((v: any) => ({
        id: String(v.id ?? ""),
        productId: String(v.product_id ?? v.productId ?? item.id ?? ""),
        variantKey: String(v.variant_key ?? v.variantKey ?? ""),
        availableQuantity: Number(v.available_quantity ?? v.availableQuantity ?? 0),
        updatedAt: v.updated_at ?? v.updatedAt,
      }))
    : [];

  // Available stock: if variants exist, sum their available quantities; otherwise use stock_quantity
  const totalVariantStock = variants.length > 0
    ? variants.reduce((sum, v) => sum + Math.max(0, v.availableQuantity), 0)
    : null;

  const rawStock = item.stock_quantity ?? item.availableStock ?? item.available_stock;
  const availableStock = totalVariantStock !== null
    ? totalVariantStock
    : typeof rawStock === "number"
      ? rawStock
      : 0;

  return {
    id: String(item.id ?? ""),
    name: item.name ?? item.title ?? "Untitled Product",
    designer: item.designer ?? item.store_name ?? "Clothify Atelier",
    category: item.category ?? "General",
    description: item.description ?? "Thoughtfully crafted fashion piece.",
    price: typeof item.price === "number" ? item.price : parseFloat(item.price || "0"),
    availableStock,
    imageUrl: item.image_url || item.imageUrl || DEFAULT_FALLBACK_IMAGE,
    color: item.color ? String(item.color) : undefined,
    isActive: typeof item.is_active === "boolean" ? item.is_active : true,
    sellerId: item.seller_id ? String(item.seller_id) : undefined,
    variants,
  };
}

export const productService = {
  async listProducts(
    queryOrFilter?: string | ProductFilter,
    sortByParam?: string,
    sortOrderParam?: string,
  ): Promise<Product[]> {
    const params = new URLSearchParams();

    if (typeof queryOrFilter === "string") {
      if (queryOrFilter.trim()) {
        params.set("search", queryOrFilter.trim());
      }
      if (sortByParam) {
        params.set("sort_by", sortByParam);
      }
      if (sortOrderParam) {
        params.set("sort_order", sortOrderParam);
      }
    } else if (queryOrFilter && typeof queryOrFilter === "object") {
      if (queryOrFilter.search?.trim()) {
        params.set("search", queryOrFilter.search.trim());
      }
      if (queryOrFilter.category?.trim()) {
        params.set("category", queryOrFilter.category.trim());
      }
      if (queryOrFilter.color?.trim()) {
        params.set("color", queryOrFilter.color.trim());
      }
      if (typeof queryOrFilter.minPrice === "number") {
        params.set("min_price", String(queryOrFilter.minPrice));
      }
      if (typeof queryOrFilter.maxPrice === "number") {
        params.set("max_price", String(queryOrFilter.maxPrice));
      }
      if (queryOrFilter.sortBy) {
        params.set("sort_by", queryOrFilter.sortBy);
      }
      if (queryOrFilter.sortOrder) {
        params.set("sort_order", queryOrFilter.sortOrder);
      }
    }

    const queryString = params.toString();
    const url = apiUrl(`/api/products${queryString ? `?${queryString}` : ""}`);

    const headers: Record<string, string> = {};
    const token = authService.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const res = await fetch(url, { headers });
    if (!res.ok) {
      const err = await res.json().catch(() => null);
      throw new Error(err?.detail || `Failed to fetch products (${res.status})`);
    }

    const data = await res.json();
    if (!Array.isArray(data)) {
      return [];
    }

    return data.map(mapApiProduct);
  },

  async getProduct(productId: string): Promise<Product | null> {
    const cleanId = productId.trim();
    if (!cleanId) return null;

    const res = await fetch(apiUrl(`/api/products/${encodeURIComponent(cleanId)}`));
    if (res.status === 404) {
      return null;
    }

    if (!res.ok) {
      const err = await res.json().catch(() => null);
      throw new Error(err?.detail || `Failed to fetch product details (${res.status})`);
    }

    const data = await res.json();
    return mapApiProduct(data);
  },

  async checkStock(
    productId: string,
    variantKey: string,
    quantity: number,
  ): Promise<StockCheckResponse> {
    const params = new URLSearchParams({
      product_id: productId,
      variant_key: variantKey,
      quantity: String(quantity),
    });

    const res = await fetch(apiUrl(`/api/products/check-stock?${params.toString()}`));
    if (!res.ok) {
      const err = await res.json().catch(() => null);
      throw new Error(err?.detail || `Stock check failed (${res.status})`);
    }

    const data = await res.json();
    return {
      productId: data.product_id,
      variantKey: data.variant_key,
      requestedQuantity: data.requested_quantity,
      availableQuantity: data.available_quantity,
      isFulfillable: data.is_fulfillable,
    };
  },

  async listSellerProducts(): Promise<Product[]> {
    const token = authService.getToken();
    if (!token) {
      throw new Error("Authentication required. Please sign in as a seller.");
    }

    const res = await fetch(apiUrl("/api/products/seller/me"), {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!res.ok) {
      const err = await res.json().catch(() => null);
      throw new Error(err?.detail || `Failed to fetch seller products (${res.status})`);
    }

    const data = await res.json();
    if (!Array.isArray(data)) return [];
    return data.map(mapApiProduct);
  },

  async createProduct(payload: ProductCreateInput): Promise<Product> {
    const token = authService.getToken();
    if (!token) {
      throw new Error("Authentication required. Please sign in as a seller.");
    }

    const res = await fetch(apiUrl("/api/products"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => null);
      throw new Error(err?.detail || `Failed to create product (${res.status})`);
    }

    const data = await res.json();
    return mapApiProduct(data);
  },

  async updateProduct(id: string, payload: ProductUpdateInput): Promise<Product> {
    const token = authService.getToken();
    if (!token) {
      throw new Error("Authentication required. Please sign in as a seller.");
    }

    const res = await fetch(apiUrl(`/api/products/${encodeURIComponent(id)}`), {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => null);
      throw new Error(err?.detail || `Failed to update product (${res.status})`);
    }

    const data = await res.json();
    return mapApiProduct(data);
  },

  async toggleProductStatus(id: string, isActive: boolean): Promise<Product> {
    return this.updateProduct(id, { is_active: isActive });
  },

  async listCategories(): Promise<string[]> {
    try {
      const res = await fetch(apiUrl("/api/products/categories"));
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // Fallback to configured categories
    }
    return [...MARKETPLACE_CATEGORIES];
  },
};
