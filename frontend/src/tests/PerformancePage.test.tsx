import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { PerformancePage } from "../features/performance/PerformancePage";

const indexStatus = {
  table: "index_lab_events",
  column: "customer_id",
  index_name: "ix_index_lab_events_customer_id_demo",
  index_exists: false,
  row_count: 100000,
};

const explainResult = {
  node_type: "Seq Scan",
  used_index: false,
  execution_time_ms: 1.9,
  planning_time_ms: 0.1,
  row_count: 200,
  plan_text: "{}",
};

const peekResult = {
  columns: ["id", "name", "stock_quantity"],
  rows: [[1, "Widget", 10]],
  row_count: 1,
};

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <PerformancePage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function mockFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string, init?: RequestInit) => {
      if (url.endsWith("/api/index-lab/status")) {
        return Promise.resolve({ ok: true, json: async () => indexStatus });
      }
      if (url.endsWith("/api/index-lab/explain")) {
        return Promise.resolve({ ok: true, json: async () => explainResult });
      }
      if (url.endsWith("/api/transaction-lab/peek-committed")) {
        return Promise.resolve({ ok: true, json: async () => peekResult });
      }
      if (url.endsWith("/api/transaction-lab/begin") && init?.method === "POST") {
        return Promise.resolve({ ok: true, json: async () => ({ session_id: "sess-1" }) });
      }
      if (url.endsWith("/api/transaction-lab/peek") && init?.method === "POST") {
        return Promise.resolve({ ok: true, json: async () => peekResult });
      }
      throw new Error(`Unexpected fetch: ${url}`);
    }),
  );
}

describe("PerformancePage", () => {
  it("shows index status and runs an explain", async () => {
    mockFetch();
    renderPage();

    expect(await screen.findByText("인덱스 없음")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /EXPLAIN ANALYZE 실행/ }));

    expect(await screen.findByText("Seq Scan")).toBeInTheDocument();
    expect(screen.getByText("순차 스캔")).toBeInTheDocument();
  });

  it("starts a transaction sandbox session and shows both panes", async () => {
    mockFetch();
    renderPage();

    await userEvent.click(screen.getByRole("tab", { name: /트랜잭션 실습/ }));
    await userEvent.click(screen.getByRole("button", { name: /BEGIN 시작/ }));

    expect(await screen.findByText(/내 트랜잭션에서 본 값/)).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "COMMIT" })).toBeInTheDocument();
  });
});
