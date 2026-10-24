import type { Order, OrderItem, OrderItemRequestInput } from "../types/marketplace";
import { authService } from "./authService";
import { apiUrl } from "./apiClient";

function mapApiOrder(data: any): Order {
  const items: OrderItem[] = Array.isArray(data.items)
    ? data.items.map((it: any) => ({
        id: String(it.id || ""),
        productId: String(it.product_id || it.productId || ""),
        stockId: it.stock_id ? String(it.stock_id) : undefined,
        variantKey: it.variant_key ? String(it.variant_key) : undefined,
        quantity: Number(it.quantity || 1),
        unitPrice: Number(it.unit_price ?? it.unitPrice ?? 0),
        lineTotal: Number(it.unit_price ?? it.unitPrice ?? 0) * Number(it.quantity || 1),
        productName: it.product_name || it.productName || undefined,
      }))
    : [];

  return {
    id: String(data.id || ""),
    status: String(data.status || "PENDING_PAYMENT"),
    createdAt: String(data.created_at || data.createdAt || new Date().toISOString()),
    updatedAt: data.updated_at ? String(data.updated_at) : undefined,
    items,
    total: typeof data.total_amount === "number" ? data.total_amount : Number(data.total || 0),
    userId: data.user_id ? String(data.user_id) : (data.userId ? String(data.userId) : undefined),
    customerEmail: data.customer_email ? String(data.customer_email) : (data.customerEmail ? String(data.customerEmail) : undefined),
    payment: data.payment ?? null,
    shipment: data.shipment ?? null,
    shipments: Array.isArray(data.shipments) ? data.shipments : (data.shipment ? [data.shipment] : []),
  };
}

export const orderService = {
  async createOrder(items: OrderItemRequestInput[]): Promise<Order> {
    const token = authService.getToken();
    if (!token) {
      throw new Error("Authentication required. Please sign in to place an order.");
    }

    if (!items || items.length === 0) {
      throw new Error("Order must contain at least one item.");
    }

    const res = await fetch(apiUrl("/api/orders/create"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ items }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => null);
      throw new Error(err?.detail || `Order creation failed (${res.status})`);
    }

    const data = await res.json();
    return mapApiOrder(data);
  },

  async getMyOrders(): Promise<Order[]> {
    const token = authService.getToken();
    if (!token) {
      return [];
    }

    const res = await fetch(apiUrl("/api/orders/my-orders"), {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!res.ok) {
      const err = await res.json().catch(() => null);
      throw new Error(err?.detail || `Failed to fetch orders (${res.status})`);
    }

    const data = await res.json();
    if (!Array.isArray(data)) return [];
    return data.map(mapApiOrder);
  },

  async getOrder(id: string): Promise<Order | null> {
    const cleanId = id.trim();
    if (!cleanId) return null;

    const token = authService.getToken();
    if (!token) {
      throw new Error("Authentication required. Please sign in to view this order.");
    }

    const res = await fetch(apiUrl(`/api/orders/${encodeURIComponent(cleanId)}`), {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (res.status === 404) {
      return null;
    }

    if (!res.ok) {
      const err = await res.json().catch(() => null);
      throw new Error(err?.detail || `Failed to fetch order (${res.status})`);
    }

    const data = await res.json();
    return mapApiOrder(data);
  },

  async cancelOrder(orderId: string): Promise<Order> {
    const cleanId = orderId.trim();
    if (!cleanId) {
      throw new Error("Order ID is required.");
    }

    const token = authService.getToken();
    if (!token) {
      throw new Error("Authentication required. Please sign in to cancel this order.");
    }

    const res = await fetch(apiUrl(`/api/orders/${encodeURIComponent(cleanId)}/cancel`), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
    });

    if (!res.ok) {
      const err = await res.json().catch(() => null);
      throw new Error(err?.detail || `Failed to cancel order (${res.status})`);
    }

    const data = await res.json();
    return mapApiOrder(data);
  },

  async simulatePayment(
    orderId: string,
    options?: {
      outcome?: "SUCCESS" | "FAILURE";
      paymentMethod?: string;
      failureReason?: string;
    },
  ): Promise<{ success: boolean; message: string; order: Order; paymentId?: string }> {
    const cleanId = orderId.trim();
    if (!cleanId) {
      throw new Error("Order ID is required.");
    }

    const token = authService.getToken();
    if (!token) {
      throw new Error("Authentication required. Please sign in to pay for this order.");
    }

    const res = await fetch(apiUrl(`/api/orders/${encodeURIComponent(cleanId)}/simulate-payment`), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        outcome: options?.outcome || "SUCCESS",
        payment_method: options?.paymentMethod || "SIMULATED_CARD",
        failure_reason: options?.failureReason,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => null);
      throw new Error(err?.detail || `Payment simulation failed (${res.status})`);
    }

    const data = await res.json();
    return {
      success: Boolean(data.success),
      message: String(data.message || ""),
      order: mapApiOrder(data.order),
      paymentId: data.payment_id ? String(data.payment_id) : undefined,
    };
  },

  async getSellerOrders(): Promise<any[]> {
    const token = authService.getToken();
    if (!token) {
      throw new Error("Authentication required. Please sign in as a seller.");
    }

    const res = await fetch(apiUrl("/api/seller/orders"), {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!res.ok) {
      const err = await res.json().catch(() => null);
      throw new Error(err?.detail || `Failed to fetch seller orders (${res.status})`);
    }

    return res.json();
  },

  async updateSellerShipment(
    orderId: string,
    payload: {
      carrier_name?: string;
      tracking_number?: string;
      status?: string;
      estimated_delivery?: string;
    }
  ): Promise<any> {
    const token = authService.getToken();
    if (!token) {
      throw new Error("Authentication required. Please sign in as a seller.");
    }

    const res = await fetch(apiUrl(`/api/seller/orders/${encodeURIComponent(orderId)}/shipment`), {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => null);
      throw new Error(err?.detail || `Failed to update shipment (${res.status})`);
    }

    return res.json();
  },
};
