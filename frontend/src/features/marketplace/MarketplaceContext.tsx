import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";
import { mockProducts } from "../../services/mockMarketplaceService";
import { authService, USER_STORAGE_KEY } from "../../services/authService";
import { orderService } from "../../services/orderService";
import type {
  CartItem,
  CartLine,
  MockUser,
  Order,
  OrderItemRequestInput,
  Product,
  ProductVariant,
  RegisterInput,
} from "../../types/marketplace";

interface MarketplaceContextValue {
  cart: CartItem[];
  cartCount: number;
  user: MockUser | null;
  token: string | null;
  addToCart(
    product: Product,
    quantity: number,
    variantKey?: string,
    stockId?: string,
  ): void;
  updateQuantity(
    productIdOrLineId: string,
    quantity: number,
    variantKey?: string,
  ): void;
  removeFromCart(productIdOrLineId: string, variantKey?: string): void;
  clearCart(): void;
  signIn(email: string, password?: string): Promise<void>;
  register(input: RegisterInput | string, email?: string): Promise<void>;
  updateUser(updates: Partial<MockUser>): Promise<void>;
  becomeSeller(storeName: string): Promise<void>;
  signOut(): void;
  checkout(): Promise<Order>;
}

const MarketplaceContext = createContext<MarketplaceContextValue | null>(null);

export const CART_STORAGE_KEY = "clothify_cart_lines";

function buildCartLineId(productId: string, variantKey?: string): string {
  return `${productId}:${variantKey || "default"}`;
}

function isValidCartLine(item: unknown): item is CartLine {
  if (!item || typeof item !== "object") return false;
  const candidate = item as Record<string, unknown>;
  if (typeof candidate.productId !== "string" || !candidate.productId.trim()) {
    return false;
  }
  if (
    typeof candidate.quantity !== "number" ||
    !Number.isFinite(candidate.quantity) ||
    candidate.quantity <= 0
  ) {
    return false;
  }
  if (candidate.variantKey !== undefined && typeof candidate.variantKey !== "string") {
    return false;
  }
  if (candidate.stockId !== undefined && typeof candidate.stockId !== "string") {
    return false;
  }
  if (candidate.id !== undefined && typeof candidate.id !== "string") {
    return false;
  }
  if (candidate.productSnapshot !== undefined) {
    if (!candidate.productSnapshot || typeof candidate.productSnapshot !== "object") {
      return false;
    }
    const snap = candidate.productSnapshot as Record<string, unknown>;
    if (typeof snap.id !== "string" || typeof snap.name !== "string" || typeof snap.price !== "number") {
      return false;
    }
  }
  return true;
}

function loadSavedCartLines(): CartLine[] {
  try {
    if (typeof window !== "undefined" && window.localStorage) {
      const raw = window.localStorage.getItem(CART_STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) {
          return parsed.filter(isValidCartLine);
        }
      }
    }
  } catch {
    // Ignore corrupt storage or access errors without crashing
  }
  return [];
}

function saveCartLinesToStorage(lines: CartLine[]): void {
  try {
    if (typeof window !== "undefined" && window.localStorage) {
      if (lines.length === 0) {
        window.localStorage.removeItem(CART_STORAGE_KEY);
      } else {
        window.localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(lines));
      }
    }
  } catch {
    // Ignore storage write errors without crashing
  }
}

function loadActiveUser(): MockUser | null {
  try {
    if (typeof window !== "undefined" && window.localStorage) {
      const raw = window.localStorage.getItem(USER_STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed && typeof parsed.email === "string") {
          return parsed;
        }
      }
    }
  } catch {
    // Ignore storage errors
  }
  return null;
}

export function MarketplaceProvider({ children }: PropsWithChildren) {
  const [cartLines, setCartLines] = useState<CartLine[]>(() => loadSavedCartLines());
  const [user, setUser] = useState<MockUser | null>(() => loadActiveUser());
  const [token, setToken] = useState<string | null>(() => authService.getToken());

  // Synchronize cart changes to localStorage
  useEffect(() => {
    saveCartLinesToStorage(cartLines);
  }, [cartLines]);

  // Check and hydrate active authentication session on initial load or refresh
  useEffect(() => {
    const savedToken = authService.getToken();
    if (savedToken) {
      authService
        .getMe(savedToken)
        .then((verifiedUser) => {
          if (verifiedUser) {
            setUser(verifiedUser);
            setToken(savedToken);
          } else {
            // Token expired or invalidated
            setUser(null);
            setToken(null);
          }
        })
        .catch(() => {
          // Keep cached state during temporary network glitch
        });
    }
  }, []);

  const addToCart = useCallback(
    (
      product: Product,
      quantity: number,
      variantKey?: string,
      stockId?: string,
    ) => {
      if (!Number.isInteger(quantity) || quantity < 1) {
        throw new Error("Choose a quantity of at least one.");
      }

      // FR-02: Prevent sellers from adding their own products to shopping bag
      if (user && product.sellerId && user.id === product.sellerId) {
        throw new Error("You cannot purchase your own atelier's piece.");
      }

      const hasVariants = Boolean(product.variants && product.variants.length > 0);
      let targetVariant: ProductVariant | undefined;
      let effectiveAvailableStock = product.availableStock;
      let effectiveStockId = stockId;

      if (hasVariants) {
        if (!variantKey) {
          throw new Error("Please select a size or variant before adding to bag.");
        }
        targetVariant = product.variants?.find((v) => v.variantKey === variantKey);
        if (!targetVariant) {
          throw new Error(`Variant "${variantKey}" is no longer available.`);
        }
        effectiveAvailableStock = targetVariant.availableQuantity;
        effectiveStockId = effectiveStockId || targetVariant.id;
      }

      const lineId = buildCartLineId(product.id, variantKey);
      const existing = cartLines.find(
        (line) => (line.id || buildCartLineId(line.productId, line.variantKey)) === lineId,
      );
      const nextQuantity = (existing?.quantity ?? 0) + quantity;

      if (nextQuantity > effectiveAvailableStock) {
        const itemLabel = variantKey ? ` in ${variantKey}` : "";
        throw new Error(
          `Only ${effectiveAvailableStock} item(s) are available${itemLabel}.`,
        );
      }

      const next = existing
        ? cartLines.map((line) =>
            (line.id || buildCartLineId(line.productId, line.variantKey)) === lineId
              ? {
                  ...line,
                  quantity: nextQuantity,
                  productSnapshot: product,
                  stockId: effectiveStockId || line.stockId,
                }
              : line,
          )
        : [
            ...cartLines,
            {
              id: lineId,
              productId: product.id,
              variantKey,
              stockId: effectiveStockId,
              quantity,
              productSnapshot: product,
            },
          ];

      setCartLines(next);
    },
    [cartLines],
  );

  const updateQuantity = useCallback(
    (target: string, quantity: number, variantKey?: string) => {
      const targetId = target.includes(":")
        ? target
        : variantKey !== undefined
        ? buildCartLineId(target, variantKey)
        : target;

      const line = cartLines.find(
        (l) =>
          l.id === targetId ||
          buildCartLineId(l.productId, l.variantKey) === targetId ||
          l.productId === targetId,
      );

      if (!line) {
        throw new Error("This item is not in your bag.");
      }

      const product =
        line.productSnapshot ||
        mockProducts.find((item) => item.id === line.productId);
      if (!product) {
        throw new Error("This product is no longer available.");
      }

      const variant =
        line.variantKey && product.variants
          ? product.variants.find((v) => v.variantKey === line.variantKey)
          : undefined;

      const availableStock = variant
        ? variant.availableQuantity
        : product.availableStock;

      if (!Number.isInteger(quantity) || quantity < 1 || quantity > availableStock) {
        throw new Error(`Choose a quantity between 1 and ${availableStock}.`);
      }

      setCartLines((prev) =>
        prev.map((l) => {
          const isMatch =
            l.id === targetId ||
            buildCartLineId(l.productId, l.variantKey) === targetId ||
            (target.includes(":") || variantKey !== undefined
              ? false
              : l.productId === targetId);
          return isMatch ? { ...l, quantity } : l;
        }),
      );
    },
    [cartLines],
  );

  const removeFromCart = useCallback((target: string, variantKey?: string) => {
    const targetId = target.includes(":")
      ? target
      : variantKey !== undefined
      ? buildCartLineId(target, variantKey)
      : target;

    setCartLines((prev) =>
      prev.filter((l) => {
        const isMatch =
          l.id === targetId ||
          buildCartLineId(l.productId, l.variantKey) === targetId ||
          (target.includes(":") || variantKey !== undefined
            ? false
            : l.productId === targetId);
        return !isMatch;
      }),
    );
  }, []);

  const signIn = useCallback(async (email: string, password?: string) => {
    const res = await authService.login(email, password);
    setToken(res.token);
    setUser(res.user);
  }, []);

  const register = useCallback(async (input: RegisterInput | string) => {
    if (typeof input === "string") {
      throw new Error("Please complete the registration form.");
    }
    const res = await authService.register(input);
    setToken(res.token);
    setUser(res.user);
  }, []);

  const updateUser = useCallback(async (updates: Partial<MockUser>) => {
    const updatedUser = await authService.updateProfile(updates);
    setUser(updatedUser);
  }, []);

  const becomeSeller = useCallback(async (storeName: string) => {
    const updatedUser = await authService.becomeSeller(storeName);
    setUser(updatedUser);
  }, []);

  const signOut = useCallback(() => {
    authService.clearSession();
    setToken(null);
    setUser(null);
  }, []);

  const checkout = useCallback(async () => {
    if (!user) {
      throw new Error("Please sign in before checkout.");
    }
    if (cartLines.length === 0) {
      throw new Error("Your shopping bag is empty.");
    }

    const items: OrderItemRequestInput[] = cartLines.map((line) => {
      let variantKey = line.variantKey?.trim();
      if (!variantKey && line.productSnapshot?.variants && line.productSnapshot.variants.length > 0) {
        variantKey = line.productSnapshot.variants[0].variantKey;
      }
      if (!variantKey) {
        variantKey = "DEFAULT";
      }

      return {
        product_id: line.productId,
        variant_key: variantKey,
        quantity: line.quantity,
      };
    });

    const order = await orderService.createOrder(items);
    setCartLines([]);
    saveCartLinesToStorage([]);
    return order;
  }, [cartLines, user]);

  const resolvedCart = useMemo<CartItem[]>(() => {
    return cartLines.flatMap((line) => {
      const product =
        line.productSnapshot ||
        mockProducts.find((item) => item.id === line.productId);
      if (!product) return [];

      const variant =
        line.variantKey && product.variants
          ? product.variants.find((v) => v.variantKey === line.variantKey)
          : undefined;

      const availableStock = variant
        ? variant.availableQuantity
        : product.availableStock;

      const lineId = line.id || buildCartLineId(line.productId, line.variantKey);

      return [
        {
          ...line,
          id: lineId,
          product,
          selectedVariant: variant,
          availableStock,
          unitPrice: product.price,
          lineTotal: product.price * line.quantity,
        },
      ];
    });
  }, [cartLines]);

  const value = useMemo<MarketplaceContextValue>(
    () => ({
      cart: resolvedCart,
      cartCount: cartLines.reduce((sum, line) => sum + line.quantity, 0),
      user,
      token,
      addToCart,
      updateQuantity,
      removeFromCart,
      clearCart: () => {
        setCartLines([]);
        saveCartLinesToStorage([]);
      },
      signIn,
      register,
      updateUser,
      becomeSeller,
      signOut,
      checkout,
    }),
    [
      addToCart,
      cartLines,
      checkout,
      register,
      removeFromCart,
      resolvedCart,
      signIn,
      signOut,
      token,
      updateQuantity,
      updateUser,
      becomeSeller,
      user,
    ],
  );

  return <MarketplaceContext.Provider value={value}>{children}</MarketplaceContext.Provider>;
}

export function useMarketplace(): MarketplaceContextValue {
  const context = useContext(MarketplaceContext);
  if (!context) throw new Error("useMarketplace must be used inside MarketplaceProvider.");
  return context;
}
