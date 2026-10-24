export const MARKETPLACE_CATEGORIES = [
  "T-Shirts",
  "Shirts",
  "Hoodies & Sweatshirts",
  "Jackets",
  "Shorts",
  "Long Pants",
  "Accessories",
] as const;

export type MarketplaceCategory = (typeof MARKETPLACE_CATEGORIES)[number];

export interface ProductVariant {
  id: string;
  productId: string;
  variantKey: string;
  availableQuantity: number;
  updatedAt?: string;
}

export interface Product {
  id: string;
  name: string;
  designer: string;
  category: string;
  description: string;
  price: number;
  availableStock: number;
  imageUrl: string;
  color?: string;
  isActive?: boolean;
  sellerId?: string;
  variants?: ProductVariant[];
}

export interface ProductFilter {
  search?: string;
  category?: string;
  color?: string;
  minPrice?: number;
  maxPrice?: number;
  sortBy?: string;
  sortOrder?: string;
}

export interface StockCheckResponse {
  productId: string;
  variantKey: string;
  requestedQuantity: number;
  availableQuantity: number;
  isFulfillable: boolean;
}

export interface CartLine {
  id?: string;
  productId: string;
  variantKey?: string;
  stockId?: string;
  quantity: number;
  productSnapshot?: Product;
}

export interface CartItem extends CartLine {
  id: string;
  product: Product;
  selectedVariant?: ProductVariant;
  availableStock: number;
  unitPrice: number;
  lineTotal: number;
}

export type UserRole = "buyer" | "seller";

export interface MockUser {
  id?: string;
  name: string;
  email: string;
  role?: UserRole;
  storeName?: string;
}

export interface RegisterInput {
  name: string;
  email: string;
  role?: UserRole;
  storeName?: string;
  password?: string;
}

export interface BecomeSellerInput {
  store_name: string;
}

export interface OrderItemRequestInput {
  product_id: string;
  variant_key: string;
  quantity: number;
}

export interface OrderCreatePayload {
  items: OrderItemRequestInput[];
}

export interface OrderItem {
  id: string;
  productId: string;
  stockId?: string;
  variantKey?: string;
  quantity: number;
  unitPrice: number;
  lineTotal: number;
  productName?: string;
}

export interface Order {
  id: string;
  status: string;
  createdAt: string;
  updatedAt?: string;
  items: (CartItem | OrderItem)[];
  total: number;
  customerEmail?: string;
  userId?: string;
  payment?: Record<string, any> | null;
  shipment?: Record<string, any> | null;
  shipments?: Record<string, any>[] | null;
}

export interface SellerOrder {
  id: string;
  user_id: string;
  status: string;
  created_at: string;
  items: {
    id: string;
    product_id: string;
    stock_id: string;
    variant_key: string;
    quantity: number;
    unit_price: number;
    product_name?: string;
  }[];
  shipment?: Record<string, any> | null;
}

export interface MarketplaceService {
  listProducts(
    queryOrFilter?: string | ProductFilter,
    sortBy?: string,
    sortOrder?: string,
  ): Promise<Product[]>;
  getProduct(productId: string): Promise<Product | null>;
  checkStock(items: CartLine[]): Promise<boolean>;
  createOrder(items: CartLine[], customerEmail: string): Promise<Order>;
  listOrders(customerEmail: string): Promise<Order[]>;
  getOrder(orderId: string, customerEmail: string): Promise<Order | null>;
  login(email: string): Promise<MockUser>;
  register(input: RegisterInput | string, email?: string): Promise<MockUser>;
  updateUser?(email: string, updates: Partial<MockUser>): MockUser | null;
}

export interface StockItemInput {
  variant_key: string;
  available_quantity: number;
}

export interface ProductCreateInput {
  name: string;
  description: string;
  price: number;
  stock_quantity?: number;
  category: string;
  color?: string;
  image_url?: string;
  variants?: StockItemInput[];
}

export interface ProductUpdateInput {
  name?: string;
  description?: string;
  price?: number;
  stock_quantity?: number;
  category?: string;
  color?: string;
  image_url?: string;
  is_active?: boolean;
  variants?: StockItemInput[];
}

