import { apiGet } from "./client";

export interface OrderSummary {
  order_number: number;
  customer_name: string;
  status: string;
  item_count: number;
  total_cents: number;
}

export interface RelationalOrderItem {
  product_id: number;
  product_name: string;
  quantity: number;
  unit_price_cents: number;
}

export interface RelationalOrderView {
  order: { id: number; order_number: number; status: string; created_at: string };
  customer: { id: number; full_name: string; email: string };
  items: RelationalOrderItem[];
  sql: string;
}

export interface DocumentOrderView {
  document: Record<string, unknown>;
}

export interface OrderComparison {
  order_number: number;
  relational: RelationalOrderView;
  document: DocumentOrderView;
}

export async function fetchOrderSummaries(): Promise<OrderSummary[]> {
  return apiGet<OrderSummary[]>("/api/comparison/orders");
}

export async function fetchOrderComparison(orderNumber: number): Promise<OrderComparison> {
  return apiGet<OrderComparison>(`/api/comparison/orders/${orderNumber}`);
}
