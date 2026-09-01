import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { NotesPage } from "../features/notes/NotesPage";

function renderPage() {
  return render(
    <MemoryRouter>
      <NotesPage />
    </MemoryRouter>,
  );
}

describe("NotesPage", () => {
  it("shows the first note expanded by default and others collapsed", () => {
    renderPage();

    expect(screen.getByText("정규화 vs 임베딩")).toBeInTheDocument();
    expect(screen.getByText(/order_items가 주문과 상품을 잇는 조인/)).toBeInTheDocument();
    expect(screen.queryByText(/BEGIN으로 시작해서/)).not.toBeInTheDocument();
  });

  it("toggles a note open and closed on click", async () => {
    renderPage();

    await userEvent.click(screen.getByText("트랜잭션"));
    expect(await screen.findByText(/BEGIN으로 시작해서/)).toBeInTheDocument();

    await userEvent.click(screen.getByText("트랜잭션"));
    expect(screen.queryByText(/BEGIN으로 시작해서/)).not.toBeInTheDocument();
  });
});
