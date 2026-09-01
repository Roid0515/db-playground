/** Tracks which practice pages the learner has actually visited, in
 * localStorage, so the sidebar's progress widget reflects real learner
 * progress instead of a static "which phase this build is on" number. */

export interface LearningStep {
  key: string;
  label: string;
}

export const LEARNING_STEPS: LearningStep[] = [
  { key: "relational", label: "관계형 DB" },
  { key: "mongodb", label: "MongoDB" },
  { key: "comparison", label: "구조 비교" },
  { key: "performance", label: "트랜잭션 · 인덱스" },
  { key: "notes", label: "학습 노트" },
];

const STORAGE_KEY = "db-playground:visited-steps";

export function getVisitedSteps(): Set<string> {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return new Set(raw ? (JSON.parse(raw) as string[]) : []);
  } catch {
    return new Set();
  }
}

export function markStepVisited(key: string): Set<string> {
  const visited = getVisitedSteps();
  if (!visited.has(key)) {
    visited.add(key);
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify([...visited]));
    } catch {
      // localStorage unavailable (private browsing, storage full, etc.) --
      // progress just won't persist across reloads.
    }
  }
  return visited;
}
