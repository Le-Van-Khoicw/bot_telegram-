export type AnyRow = Record<string, any>;

export interface AdminSnapshot {
  brand?: {
    shop_name?: string;
    admin_title?: string;
  };
  generated_at: string;
  timezone: string;
  summary: {
    orders: number;
    revenue: number;
    status_counts: Record<string, number>;
    users: number;
    stock_ready: number;
    stock_held: number;
    stock_sold: number;
  };
  products: AnyRow[];
  orders: AnyRow[];
  users: AnyRow[];
  pool: AnyRow[];
  reservations: AnyRow[];
  fulfillments: AnyRow[];
  deliveries?: AnyRow[];
  materials?: AnyRow[];
  expenses?: AnyRow[];
  promotions?: AnyRow[];
  promo_awards?: AnyRow[];
  promo_settings?: AnyRow;
  slots?: AnyRow[];
  slot_participants?: AnyRow[];
}

export async function adminApi<T>(path: string, key: string, options: RequestInit = {}): Promise<T> {
  const sep = path.includes("?") ? "&" : "?";
  const res = await fetch(`${path}${sep}key=${encodeURIComponent(key)}`, {
    headers: { "content-type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    let message = body;
    try {
      const parsed = JSON.parse(body);
      message = parsed.detail || parsed.message || body;
    } catch {
      // Keep the raw body when the server did not return JSON.
    }
    throw new Error(message || `HTTP ${res.status}`);
  }
  return res.json();
}

export const money = (value: any) => `${Number(value || 0).toLocaleString("vi-VN")}đ`;

export const text = (value: any) => (value === null || value === undefined || value === "" ? "—" : String(value));
