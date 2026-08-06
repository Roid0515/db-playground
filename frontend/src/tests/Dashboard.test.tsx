import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Dashboard } from "../features/dashboard/Dashboard";

const healthyResponse = {
  status: "healthy",
  services: {
    postgres: {
      service: "PostgreSQL",
      status: "healthy",
      latency_ms: 4.2,
      checked_at: "2026-08-06T10:00:00Z",
      message: "Connection established",
    },
    mongodb: {
      service: "MongoDB",
      status: "healthy",
      latency_ms: 5.1,
      checked_at: "2026-08-06T10:00:00Z",
      message: "Connection established",
    },
  },
};

function renderDashboard() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <Dashboard />
    </QueryClientProvider>,
  );
}

describe("Dashboard", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => healthyResponse }));
  });

  it("shows both database connection states", async () => {
    renderDashboard();
    expect(await screen.findByText("모든 시스템 정상")).toBeInTheDocument();
    expect(screen.getByLabelText("PostgreSQL 연결 상태")).toHaveTextContent("4.2 ms");
    expect(screen.getByLabelText("MongoDB 연결 상태")).toHaveTextContent("5.1 ms");
  });

  it("refreshes health when requested", async () => {
    renderDashboard();
    await screen.findByText("모든 시스템 정상");
    await userEvent.click(screen.getByRole("button", { name: "상태 새로고침" }));
    expect(fetch).toHaveBeenCalledTimes(2);
  });
});