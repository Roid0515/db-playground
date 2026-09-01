/** Single source of truth for the current-phase labels shown across the
 * sidebar, dashboard, and every page's footer -- previously each of those
 * had its own copy of "Phase 03" / "3 / 7 단계" / etc, which drift the
 * moment one gets updated and the others don't. */
export const CURRENT_PHASE_NUMBER = 3;
export const TOTAL_PHASES = 7;
export const CURRENT_PHASE_TITLE = "관계형 DB 실습";
export const CURRENT_PHASE_TITLE_EN = "Relational Practice";

const paddedNumber = String(CURRENT_PHASE_NUMBER).padStart(2, "0");

export const PHASE_LABEL = `Phase ${paddedNumber}`;
export const PHASE_FOOTER_LABEL = `${PHASE_LABEL} / ${CURRENT_PHASE_TITLE_EN}`;
export const PHASE_SCOPE_NOTE = `Phase ${CURRENT_PHASE_NUMBER} 범위 밖`;
export const PHASE_PROGRESS_LABEL = `${CURRENT_PHASE_NUMBER} / ${TOTAL_PHASES} 단계`;
export const PHASE_PROGRESS_PERCENT = (CURRENT_PHASE_NUMBER / TOTAL_PHASES) * 100;
