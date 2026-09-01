import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import { Sidebar } from "../components/Sidebar";
import { LEARNING_STEPS, markStepVisited } from "../lib/learningProgress";

function renderSidebar(activeLabel: string) {
  return render(
    <MemoryRouter>
      <Sidebar activeLabel={activeLabel} />
    </MemoryRouter>,
  );
}

describe("Sidebar learning-progress widget", () => {
  afterEach(() => {
    window.localStorage.clear();
  });

  it("starts at 0 / N and shows what's currently being viewed", () => {
    renderSidebar("관계형 DB");
    expect(screen.getByText("학습 진행상황")).toBeInTheDocument();
    // Rendering itself marks the active step visited, so by the time we
    // assert, this specific page counts as 1 already -- this is the point
    // of the widget (real progress, not a static number).
    expect(screen.getByText(`1 / ${LEARNING_STEPS.length} 완료`)).toBeInTheDocument();
    expect(screen.getByText("지금 보는 중: 관계형 DB")).toBeInTheDocument();
  });

  it("does not count the dashboard itself as a learning step", () => {
    renderSidebar("대시보드");
    expect(screen.getByText(`0 / ${LEARNING_STEPS.length} 완료`)).toBeInTheDocument();
    expect(screen.getByText(`다음 추천: ${LEARNING_STEPS[0].label}`)).toBeInTheDocument();
  });

  it("accumulates real visits across separate page views", () => {
    renderSidebar("관계형 DB").unmount();
    renderSidebar("MongoDB").unmount();
    renderSidebar("대시보드");
    expect(screen.getByText(`2 / ${LEARNING_STEPS.length} 완료`)).toBeInTheDocument();
  });

  it("shows a completion message once every step has been visited", () => {
    for (const step of LEARNING_STEPS) markStepVisited(step.key);
    renderSidebar("대시보드");
    expect(
      screen.getByText(`${LEARNING_STEPS.length} / ${LEARNING_STEPS.length} 완료`),
    ).toBeInTheDocument();
    expect(screen.getByText("모든 단계를 완료했습니다!")).toBeInTheDocument();
    expect(screen.getByText("학습 여정 완료")).toBeInTheDocument();
  });
});
