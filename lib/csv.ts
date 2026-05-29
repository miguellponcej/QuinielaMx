import type { DashboardOrder } from "@/lib/types";

function escapeCsv(value: string | number) {
  const text = String(value);
  if (!/[",\n]/.test(text)) {
    return text;
  }

  return `"${text.replace(/"/g, '""')}"`;
}

export function ordersToCsv(orders: DashboardOrder[]) {
  const rows = [
    ["order_id", "product", "customer", "amount", "currency", "status", "created_at"],
    ...orders.map((order) => [
      order.id,
      order.productTitle,
      order.customerEmail,
      (order.amountCents / 100).toFixed(2),
      order.currency,
      order.status,
      order.createdAt
    ])
  ];

  return rows.map((row) => row.map(escapeCsv).join(",")).join("\n");
}
