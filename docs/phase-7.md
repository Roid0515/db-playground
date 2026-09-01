# Phase 7 scope

## Included

- A "학습 노트" page: a static, read-only reference summarizing the concepts covered across Phases 3-6 (normalization vs. embedding, SQL vs. mongosh syntax, transactions and isolation, indexes and query plans, and a feature-comparison table), presented as expandable cards
- Frontend tests covering the default-open/collapse behavior
- This was the last undefined phase; `CURRENT_PHASE_NUMBER`/`TOTAL_PHASES` in `frontend/src/config/phase.ts` now both read `7`, and the dashboard's roadmap section shows a completion state instead of "coming next" cards

## Deliberately deferred

No further phases were scoped as part of this work order. This page is intentionally read-only content, not a note-taking feature (learners write their own notes elsewhere) -- see the AskUserQuestion round that scoped this phase for that decision.

## Why no backend

Every other phase added at least one API. This one doesn't: the content is static prose and code-comparison tables that don't depend on the current dataset, so there's nothing to fetch or persist. Keeping it a pure frontend component avoids inventing an endpoint whose only job would be returning the same hardcoded strings the component could just hold directly.
