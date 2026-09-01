import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { RelationalPage } from "../features/relational/RelationalPage";

const tables = [
  {
    name: "customers",
    row_count: 2,
    columns: [
      { name: "id", type: "INTEGER" },
      { name: "email", type: "VARCHAR" },
    ],
  },
  { name: "products", row_count: 1, columns: [{ name: "id", type: "INTEGER" }] },
];

const customerRows = {
  columns: ["id", "email"],
  rows: [
    [1, "a@example.com"],
    [2, "b@example.com"],
  ],
  total: 2,
  page: 1,
  page_size: 20,
};

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <RelationalPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function mockFetch(overrides: { onQuery?: (sql: string) => { status: number; body: unknown } } = {}) {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string, init?: RequestInit) => {
      if (url.endsWith("/api/postgres/tables")) {
        return Promise.resolve({ ok: true, json: async () => tables });
      }
      if (url.includes("/rows")) {
        return Promise.resolve({ ok: true, json: async () => customerRows });
      }
      if (url.endsWith("/api/postgres/query") && init?.method === "POST") {
        const { sql } = JSON.parse(init.body as string);
        const result = overrides.onQuery?.(sql) ?? {
          status: 200,
          body: {
            columns: ["id"],
            rows: [[1]],
            row_count: 1,
            truncated: false,
            duration_ms: 0.5,
            statement_type: "SELECT",
          },
        };
        return Promise.resolve({ ok: result.status < 400, json: async () => result.body });
      }
      throw new Error(`Unexpected fetch: ${url}`);
    }),
  );
}

describe("RelationalPage", () => {
  it("lists tables and browses the first table's rows by default", async () => {
    mockFetch();
    renderPage();

    expect(await screen.findByText("customers")).toBeInTheDocument();
    expect(screen.getByText("products")).toBeInTheDocument();
    expect(await screen.findByText("a@example.com")).toBeInTheDocument();
  });

  it("runs a query from the SQL console and shows results", async () => {
    mockFetch({
      onQuery: () => ({
        status: 200,
        body: {
          columns: ["count"],
          rows: [[2]],
          row_count: 1,
          truncated: false,
          duration_ms: 1.1,
          statement_type: "SELECT",
        },
      }),
    });
    renderPage();

    await screen.findByText("customers");
    await userEvent.click(screen.getByRole("tab", { name: /SQL 실행/ }));
    await userEvent.click(screen.getByRole("button", { name: /실행/ }));

    await waitFor(() => {
      expect(screen.getByText("SELECT")).toBeInTheDocument();
    });
    expect(screen.getByText("1행 반환")).toBeInTheDocument();
  });

  it("shows a validation error for disallowed SQL", async () => {
    mockFetch({
      onQuery: () => ({
        status: 400,
        body: { detail: "'DROP' 문은 지원하지 않습니다." },
      }),
    });
    renderPage();

    await screen.findByText("customers");
    await userEvent.click(screen.getByRole("tab", { name: /SQL 실행/ }));
    const editor = screen.getByRole("textbox");
    await userEvent.clear(editor);
    await userEvent.type(editor, "DROP TABLE customers");
    await userEvent.click(screen.getByRole("button", { name: /실행/ }));

    expect(await screen.findByRole("alert")).toHaveTextContent("'DROP' 문은 지원하지 않습니다.");
  });
});
