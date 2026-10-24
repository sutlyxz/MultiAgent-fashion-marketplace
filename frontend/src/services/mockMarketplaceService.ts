import type {
  CartItem,
  CartLine,
  MarketplaceService,
  MockUser,
  Order,
  Product,
  ProductFilter,
  RegisterInput,
} from "../types/marketplace";
import { productService } from "./productService";

export const mockProducts: Product[] = [
  {
    id: "linen-shirt",
    name: "Relaxed Linen Shirt",
    designer: "Studio Sol",
    category: "Shirts",
    description:
      "An easy, breathable linen shirt with a softly structured collar and natural shell buttons.",
    price: 78,
    availableStock: 8,
    imageUrl:
      "https://images.unsplash.com/photo-1598033129183-c4f50c736f10?auto=format&fit=crop&w=1000&q=85",
    color: "Natural",
  },
  {
    id: "everyday-tote",
    name: "Everyday Canvas Tote",
    designer: "Form & Field",
    category: "Accessories",
    description:
      "A sturdy cotton-canvas carryall with generous room for everything the day brings.",
    price: 42,
    availableStock: 5,
    imageUrl:
      "https://images.unsplash.com/photo-1590874103328-eac38a683ce7?auto=format&fit=crop&w=1000&q=85",
    color: "Warm white",
  },
  {
    id: "soft-knit",
    name: "Soft Rib Knit",
    designer: "Sunday Works",
    category: "Hoodies & Sweatshirts",
    description:
      "A lightweight ribbed layer designed for slow mornings and long, unhurried evenings.",
    price: 96,
    availableStock: 0,
    imageUrl:
      "https://images.unsplash.com/photo-1576566588028-4147f3842f27?auto=format&fit=crop&w=1000&q=85",
    color: "Moss",
  },
  {
    id: "leather-sandals",
    name: "Tide Leather Sandals",
    designer: "Coastline",
    category: "Accessories",
    description:
      "Minimal leather sandals with a cushioned footbed and a timeless, easy profile.",
    price: 115,
    availableStock: 3,
    imageUrl:
      "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?auto=format&fit=crop&w=1000&q=85",
    color: "Cognac",
  },
  {
    id: "weekend-trousers",
    name: "Weekend Wide-Leg Trousers",
    designer: "Studio Sol",
    category: "Long Pants",
    description:
      "Softly tailored trousers cut from a fluid fabric for comfort that still feels considered.",
    price: 124,
    availableStock: 6,
    imageUrl:
      "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?auto=format&fit=crop&w=1000&q=85",
    color: "Stone",
  },
  {
    id: "woven-pouch",
    name: "Woven Market Pouch",
    designer: "Form & Field",
    category: "Accessories",
    description:
      "A hand-finished woven pouch for the small essentials you want to keep close.",
    price: 54,
    availableStock: 4,
    imageUrl:
      "https://images.unsplash.com/photo-1584917865442-de89df76afd3?auto=format&fit=crop&w=1000&q=85",
    color: "Terracotta",
  },
];

const ORDERS_STORAGE_KEY = "clothify_orders";

function loadOrders(): Order[] {
  try {
    if (typeof window !== "undefined" && window.localStorage) {
      const raw = window.localStorage.getItem(ORDERS_STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed)) return parsed;
      }
    }
  } catch {
    // Storage access unavailable
  }
  return [];
}

function saveOrders(items: Order[]): void {
  try {
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.setItem(ORDERS_STORAGE_KEY, JSON.stringify(items));
    }
  } catch {
    // Storage access unavailable
  }
}

let orders: Order[] = loadOrders();
let orderSequence = 1;
const wait = (milliseconds = 140) =>
  new Promise<void>((resolve) => window.setTimeout(resolve, milliseconds));

function snapshotCart(lines: CartLine[]): CartItem[] {
  return lines.map((line) => {
    const lineItem = line as unknown as Partial<CartItem>;
    const product =
      lineItem.product ||
      line.productSnapshot ||
      mockProducts.find((item) => item.id === line.productId);

    if (!product || line.quantity < 1) {
      throw new Error("A cart item is unavailable or exceeds current mock stock.");
    }

    const variant =
      line.variantKey && product.variants
        ? product.variants.find((v) => v.variantKey === line.variantKey)
        : undefined;

    const availableStock = variant
      ? variant.availableQuantity
      : product.availableStock;

    if (line.quantity > availableStock) {
      const label = line.variantKey ? ` in ${line.variantKey}` : "";
      throw new Error(
        `Only ${availableStock} item(s) are available for ${product.name}${label}.`,
      );
    }

    const lineId = line.id || `${line.productId}:${line.variantKey || "default"}`;

    return {
      ...line,
      id: lineId,
      product,
      selectedVariant: variant,
      availableStock,
      unitPrice: product.price,
      lineTotal: product.price * line.quantity,
    };
  });
}

const USERS_STORAGE_KEY = "clothify_registered_users";

const DEFAULT_MOCK_USERS: MockUser[] = [
  {
    name: "Evelyn Vance",
    email: "evelyn@clothify.luxury",
    role: "buyer",
  },
  {
    name: "Laurent Atelier",
    email: "laurent@clothify.luxury",
    role: "seller",
    storeName: "Maison Laurent Atelier",
  },
];

function loadRegisteredUsers(): MockUser[] {
  try {
    if (typeof window !== "undefined" && window.localStorage) {
      const raw = window.localStorage.getItem(USERS_STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed;
        }
      }
    }
  } catch {
    // Storage access unavailable, fallback to defaults
  }
  return [...DEFAULT_MOCK_USERS];
}

function saveRegisteredUsers(users: MockUser[]): void {
  try {
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.setItem(USERS_STORAGE_KEY, JSON.stringify(users));
    }
  } catch {
    // Storage access unavailable
  }
}

let registeredUsers: MockUser[] = loadRegisteredUsers();

export const mockMarketplaceService: MarketplaceService = {
  async listProducts(queryOrFilter?: string | ProductFilter, sortBy = "", sortOrder = "") {
    return productService.listProducts(queryOrFilter, sortBy, sortOrder);
  },

  async getProduct(productId) {
    return productService.getProduct(productId);
  },

  async checkStock(lines) {
    await wait();
    return lines.length > 0 && lines.every((line) => {
      const product = mockProducts.find((item) => item.id === line.productId);
      return Boolean(
        product &&
          Number.isInteger(line.quantity) &&
          line.quantity > 0 &&
          line.quantity <= product.availableStock,
      );
    });
  },

  async createOrder(lines, customerEmail) {
    await wait(220);
    const cleanEmail = customerEmail.trim();
    if (!cleanEmail) {
      throw new Error("Sign in with a demo account before placing a mock order.");
    }

    const user = registeredUsers.find((u) => u.email.toLowerCase() === cleanEmail.toLowerCase());
    if (user && user.role === "seller") {
      for (const line of lines) {
        const prod = mockProducts.find((p) => p.id === line.productId) || line.productSnapshot;
        if (prod && prod.sellerId && prod.sellerId === user.id) {
          throw new Error(`Sellers cannot purchase their own products (${prod.name}).`);
        }
      }
    }

    const items = snapshotCart(lines);
    const order: Order = {
      id: `DEMO-${String(orderSequence++).padStart(4, "0")}`,
      status: "MOCK_ONLY_NOT_PAID",
      createdAt: new Date().toISOString(),
      items,
      total: items.reduce((sum, item) => sum + item.lineTotal, 0),
      customerEmail: cleanEmail,
    };
    orders = loadOrders();
    orders.unshift(order);
    saveOrders(orders);
    return order;
  },

  async listOrders(customerEmail) {
    await wait();
    const target = customerEmail.trim().toLowerCase();
    orders = loadOrders();
    return orders.filter(
      (order) => order.customerEmail?.trim().toLowerCase() === target,
    );
  },

  async getOrder(orderId, customerEmail) {
    await wait();
    const target = customerEmail.trim().toLowerCase();
    orders = loadOrders();
    return (
      orders.find(
        (order) =>
          order.id === orderId &&
          order.customerEmail?.trim().toLowerCase() === target,
      ) ?? null
    );
  },

  async login(email) {
    await wait();
    const cleanEmail = email.trim();
    if (!cleanEmail.includes("@")) {
      throw new Error("Enter a valid email address for the demo sign-in.");
    }

    // Refresh from storage to ensure latest registered accounts
    registeredUsers = loadRegisteredUsers();
    const found = registeredUsers.find(
      (u) => u.email.trim().toLowerCase() === cleanEmail.toLowerCase(),
    );

    if (found) {
      return {
        name: found.name,
        email: found.email,
        role: found.role,
        storeName: found.storeName,
      };
    }

    throw new Error(
      "No account found with this email. Please check your email or create an account.",
    );
  },

  async register(input: RegisterInput | string, emailStr?: string): Promise<MockUser> {
    await wait();
    registeredUsers = loadRegisteredUsers();

    if (typeof input === "string") {
      const email = (emailStr || "").trim();
      if (!input.trim() || !email.includes("@")) {
        throw new Error("Enter a name and valid email address to continue.");
      }
      const newUser: MockUser = { name: input.trim(), email, role: "buyer" };
      const idx = registeredUsers.findIndex(
        (u) => u.email.trim().toLowerCase() === email.toLowerCase(),
      );
      if (idx >= 0) {
        registeredUsers[idx] = newUser;
      } else {
        registeredUsers.push(newUser);
      }
      saveRegisteredUsers(registeredUsers);
      return newUser;
    }

    const { name, email, role, storeName } = input;
    if (!name.trim()) {
      throw new Error("Full name is required.");
    }
    const cleanEmail = email.trim();
    if (!cleanEmail || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(cleanEmail)) {
      throw new Error("Enter a valid email address.");
    }
    if (role !== "buyer" && role !== "seller") {
      throw new Error("Please select a valid account role.");
    }
    if (role === "seller" && (!storeName || !storeName.trim())) {
      throw new Error("Store name is required for seller accounts.");
    }

    const newUser: MockUser = {
      name: name.trim(),
      email: cleanEmail,
      role,
      storeName: role === "seller" && storeName ? storeName.trim() : undefined,
    };

    const idx = registeredUsers.findIndex(
      (u) => u.email.trim().toLowerCase() === cleanEmail.toLowerCase(),
    );
    if (idx >= 0) {
      registeredUsers[idx] = newUser;
    } else {
      registeredUsers.push(newUser);
    }
    saveRegisteredUsers(registeredUsers);
    return newUser;
  },

  updateUser(email: string, updates: Partial<MockUser>): MockUser {
    registeredUsers = loadRegisteredUsers();
    const cleanOldEmail = email.trim().toLowerCase();
    const idx = registeredUsers.findIndex(
      (u) => u.email.trim().toLowerCase() === cleanOldEmail,
    );
    if (idx < 0) {
      throw new Error("Account not found.");
    }

    let nextEmail = registeredUsers[idx].email;
    if (updates.email) {
      const candidateEmail = updates.email.trim();
      const candidateLower = candidateEmail.toLowerCase();
      if (candidateLower !== cleanOldEmail) {
        const conflict = registeredUsers.find(
          (u, i) => i !== idx && u.email.trim().toLowerCase() === candidateLower,
        );
        if (conflict) {
          throw new Error("An account with this email address already exists.");
        }
        nextEmail = candidateEmail;
      }
    }

    const updatedUser: MockUser = {
      ...registeredUsers[idx],
      ...updates,
      email: nextEmail,
    };
    registeredUsers[idx] = updatedUser;
    saveRegisteredUsers(registeredUsers);

    // Migrate orders if email changed
    if (nextEmail.trim().toLowerCase() !== cleanOldEmail) {
      orders = loadOrders();
      let migrated = false;
      for (const ord of orders) {
        if (ord.customerEmail?.trim().toLowerCase() === cleanOldEmail) {
          ord.customerEmail = nextEmail;
          migrated = true;
        }
      }
      if (migrated) {
        saveOrders(orders);
      }
    }

    return updatedUser;
  },
};

export function totalFor(lines: CartLine[]): number {
  return lines.reduce((sum, line) => {
    const lineItem = line as unknown as Partial<CartItem>;
    if (typeof lineItem.lineTotal === "number") {
      return sum + lineItem.lineTotal;
    }
    const product =
      lineItem.product ||
      line.productSnapshot ||
      mockProducts.find((p) => p.id === line.productId);
    return sum + (product ? product.price * line.quantity : 0);
  }, 0);
}
