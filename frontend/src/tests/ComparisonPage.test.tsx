import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ComparisonPage } from "../features/comparison/ComparisonPage";

const orders = [
  { order_number: 1, customer_name: "Jane Doe", status: "paid", item_count: 2, total_cents: 5000 },
  { order_number: 2, customer_name: "John Smith", status: "pending", item_count: 1, total_cents: 3000 },
];

function comparisonFor(orderNumber: number) {
  return {
    order_number: orderNumber,
    relational: {
      order: { id: 1, order_number: orderNumber, status: "paid", created_at: "2026-01-01T00:00:00Z" },
      customer: { id: 1, full_name: "Jane Doe", email: "jane@example.com" },
      items: [{ product_id: 1, product_name: "Widget", quantity: 2, unit_price_cents: 2500 }],
      sql: "SELECT ... WHERE o.order_number = 1;",
    },
    document: {
      document: {
        _id: "abc123",
        order_number: orderNumber,
        items: [{ product_name: "Widget", quantity: 2, unit_price_cents: 2500 }],
      },
    },
  };
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ComparisonPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function mockFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      if (url.endsWith("/api/comparison/orders")) {
        return Promise.resolve({ ok: true, json: async () => orders });
      }
      const match = url.match(/\/api\/comparison\/orders\/(\d+)$/);
      if (match) {
        return Promise.resolve({ ok: true, json: async () => comparisonFor(Number(match[1])) });
      }
      throw new Error(`Unexpected fetch: ${url}`);
    }),
  );
}

describe("ComparisonPage", () => {
  it("lists orders and shows both structures for the first order by default", async () => {
    mockFetch();
    renderPage();

    expect(await screen.findByText(/Jane Doe/)).toBeInTheDocument();
    expect(screen.getByText(/John Smith/)).toBeInTheDocument();
    expect(await screen.findByText("PostgreSQL · 정규화 테이블 조인")).toBeInTheDocument();
    expect(screen.getByText("MongoDB · 임베디드 문서")).toBeInTheDocument();
    expect(screen.getAllByText("Widget").length).toBeGreaterThan(0);
  });

  it("switches to the selected order's comparison", async () => {
    mockFetch();
    renderPage();

    await screen.findByText(/Jane Doe/);
    await userEvent.click(screen.getByText(/John Smith/));

    await screen.findByText("MongoDB · 임베디드 문서");
    const documentCard = document.querySelectorAll(".document-card")[1];
    expect(documentCard?.textContent).toContain('"order_number": 2');
  });
});
