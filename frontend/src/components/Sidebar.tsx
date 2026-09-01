import {
  BookOpen,
  Boxes,
  Database,
  GitCompareArrows,
  LayoutDashboard,
  LockKeyhole,
  Zap,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { LEARNING_STEPS, getVisitedSteps, markStepVisited } from "../lib/learningProgress";

interface NavItem {
  label: string;
  icon: typeof Database;
  href?: string;
}

const navItems: NavItem[] = [
  { label: "대시보드", icon: LayoutDashboard, href: "/" },
  { label: "관계형 DB", icon: Database, href: "/relational" },
  { label: "MongoDB", icon: Boxes, href: "/mongodb" },
  { label: "구조 비교", icon: GitCompareArrows, href: "/comparison" },
  { label: "트랜잭션 · 인덱스", icon: Zap, href: "/performance" },
  { label: "학습 노트", icon: BookOpen, href: "/notes" },
];

export function Sidebar({ activeLabel }: { activeLabel: string }) {
  const activeStep = LEARNING_STEPS.find((step) => step.label === activeLabel);
  const [visited, setVisited] = useState<Set<string>>(() => getVisitedSteps());

  useEffect(() => {
    if (activeStep) {
      setVisited(markStepVisited(activeStep.key));
    }
  }, [activeStep]);

  const visitedCount = LEARNING_STEPS.filter((step) => visited.has(step.key)).length;
  const progressPercent = (visitedCount / LEARNING_STEPS.length) * 100;
  const nextStep = LEARNING_STEPS.find((step) => !visited.has(step.key));
  const statusText = activeStep
    ? `지금 보는 중: ${activeStep.label}`
    : nextStep
      ? `다음 추천: ${nextStep.label}`
      : "모든 단계를 완료했습니다!";
  const remainingLabel =
    LEARNING_STEPS.length - visitedCount === 0
      ? "학습 여정 완료"
      : `${LEARNING_STEPS.length - visitedCount}개 단계 남음`;

  return (
    <aside className="sidebar">
      <Link className="brand" to="/" aria-label="DB Playground 홈">
        <span className="brand-mark">
          <Database size={19} />
        </span>
        <span>
          <strong>DB</strong> Playground
        </span>
      </Link>
      <nav aria-label="주요 메뉴">
        <p className="nav-label">Workspace</p>
        {navItems.map(({ label, icon: Icon, href }) => {
          const isActive = label === activeLabel;
          if (href) {
            return (
              <Link className={`nav-item ${isActive ? "active" : ""}`} key={label} to={href}>
                <Icon size={18} strokeWidth={1.8} />
                <span>{label}</span>
              </Link>
            );
          }
          return (
            <button className="nav-item" key={label} disabled title="다음 단계에서 제공됩니다">
              <Icon size={18} strokeWidth={1.8} />
              <span>{label}</span>
              <LockKeyhole className="nav-lock" size={13} />
            </button>
          );
        })}
      </nav>
      <div className="phase-card">
        <span className="phase-kicker">학습 진행상황</span>
        <strong>
          {visitedCount} / {LEARNING_STEPS.length} 완료
        </strong>
        <p>{statusText}</p>
        <div className="phase-progress">
          <span style={{ width: `${progressPercent}%` }} />
        </div>
        <small>{remainingLabel}</small>
      </div>
      <div className="sidebar-foot">
        <span className="local-dot" /> localhost 전용
      </div>
    </aside>
  );
}
