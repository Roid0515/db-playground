import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { MongoPage } from "../features/mongo/MongoPage";

const collections = [
  { name: "customers", document_count: 2, sample_fields: ["_id", "email"] },
  { name: "products", document_count: 1, sample_fields: ["_id", "name"] },
];

const customerDocuments = {
  documents: [
    { _id: "1", email: "a@example.com" },
    { _id: "2", email: "b@example.com" },
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
        <MongoPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function mockFetch(
  overrides: { onQuery?: (command: string) => { status: number; body: unknown } } = {},
) {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string, init?: RequestInit) => {
      if (url.endsWith("/api/mongodb/collections")) {
        return Promise.resolve({ ok: true, json: async () => collections });
      }
      if (url.includes("/documents")) {
        return Promise.resolve({ ok: true, json: async () => customerDocuments });
      }
      if (url.endsWith("/api/mongodb/query") && init?.method === "POST") {
        const { command } = JSON.parse(init.body as string);
        const result = overrides.onQuery?.(command) ?? {
          status: 200,
          body: {
            documents: [{ _id: "1" }],
            row_count: 1,
            truncated: false,
            duration_ms: 0.5,
            operation: "find",
          },
        };
        return Promise.resolve({ ok: result.status < 400, json: async () => result.body });
      }
      throw new Error(`Unexpected fetch: ${url}`);
    }),
  );
}

describe("MongoPage", () => {
  it("lists collections and browses the first collection's documents by default", async () => {
    mockFetch();
    renderPage();

    expect(await screen.findByText("customers")).toBeInTheDocument();
    expect(screen.getByText("products")).toBeInTheDocument();
    expect(await screen.findByText(/a@example.com/)).toBeInTheDocument();
  });

  it("runs a command from the console and shows results", async () => {
    mockFetch({
      onQuery: () => ({
        status: 200,
        body: {
          documents: [{ _id: "1", status: "active" }, { _id: "2", status: "active" }],
          row_count: 2,
          truncated: false,
          duration_ms: 1.1,
          operation: "find",
        },
      }),
    });
    renderPage();

    await screen.findByText("customers");
    await userEvent.click(screen.getByRole("tab", { name: /명령 실행/ }));
    await userEvent.click(screen.getByRole("button", { name: /실행/ }));

    await waitFor(() => {
      expect(screen.getByText("find")).toBeInTheDocument();
    });
    expect(screen.getByText("2건 반환")).toBeInTheDocument();
  });

  it("shows a validation error for disallowed operations", async () => {
    mockFetch({
      onQuery: () => ({
        status: 400,
        body: { detail: "'drop' 연산은 지원하지 않습니다." },
      }),
    });
    renderPage();

    await screen.findByText("customers");
    await userEvent.click(screen.getByRole("tab", { name: /명령 실행/ }));
    const editor = screen.getByRole("textbox");
    await userEvent.clear(editor);
    await userEvent.type(editor, "db.customers.drop()");
    await userEvent.click(screen.getByRole("button", { name: /실행/ }));

    expect(await screen.findByRole("alert")).toHaveTextContent("'drop' 연산은 지원하지 않습니다.");
  });
});
