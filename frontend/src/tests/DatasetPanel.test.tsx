import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DatasetPanel } from "../features/dataset/DatasetPanel";

const emptyStatus = {
  postgres: { customers: 0, products: 0, orders: 0 },
  mongodb: { customers: 0, products: 0, orders: 0 },
};

const seededStatus = {
  postgres: { customers: 24, products: 18, orders: 40 },
  mongodb: { customers: 24, products: 18, orders: 40 },
};

function renderPanel() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <DatasetPanel />
    </QueryClientProvider>,
  );
}

describe("DatasetPanel", () => {
  it("generates the dataset and shows the returned counts", async () => {
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (init?.method === "POST" && url.endsWith("/api/dataset/generate")) {
        return Promise.resolve({ ok: true, json: async () => seededStatus });
      }
      return Promise.resolve({ ok: true, json: async () => emptyStatus });
    });
    vi.stubGlobal("fetch", fetchMock);

    renderPanel();
    await waitFor(() => {
      expect(screen.getByLabelText("PostgreSQL 데이터 현황")).toHaveTextContent("0");
    });

    await userEvent.click(screen.getByRole("button", { name: /샘플 데이터 생성/ }));

    await waitFor(() => {
      expect(screen.getByLabelText("PostgreSQL 데이터 현황")).toHaveTextContent("40");
    });
    expect(screen.getByLabelText("MongoDB 데이터 현황")).toHaveTextContent("40");
  });

  it("resets the dataset back to zero", async () => {
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (init?.method === "POST" && url.endsWith("/api/dataset/reset")) {
        return Promise.resolve({ ok: true, json: async () => emptyStatus });
      }
      return Promise.resolve({ ok: true, json: async () => seededStatus });
    });
    vi.stubGlobal("fetch", fetchMock);

    renderPanel();
    await screen.findByText(/40/);

    await userEvent.click(screen.getByRole("button", { name: "초기화" }));

    expect(await screen.findByLabelText("PostgreSQL 데이터 현황")).toHaveTextContent("0");
  });

  it("shows an error message when generation fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) => {
        if (init?.method === "POST") {
          return Promise.resolve({ ok: false, json: async () => ({}) });
        }
        return Promise.resolve({ ok: true, json: async () => emptyStatus });
      }),
    );

    renderPanel();
    await screen.findByLabelText("PostgreSQL 데이터 현황");
    await userEvent.click(screen.getByRole("button", { name: /샘플 데이터 생성/ }));

    expect(await screen.findByRole("alert")).toHaveTextContent("샘플 데이터 생성에 실패했습니다.");
  });
});
