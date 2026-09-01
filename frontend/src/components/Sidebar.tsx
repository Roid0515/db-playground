import { BookOpen, Boxes, Database, GitCompareArrows, LayoutDashboard, LockKeyhole } from "lucide-react";
import { Link } from "react-router-dom";
import {
  CURRENT_PHASE_TITLE,
  PHASE_LABEL,
  PHASE_PROGRESS_LABEL,
  PHASE_PROGRESS_PERCENT,
} from "../config/phase";

interface NavItem {
  label: string;
  icon: typeof Database;
  href?: string;
}

const navItems: NavItem[] = [
  { label: "대시보드", icon: LayoutDashboard, href: "/" },
  { label: "관계형 DB", icon: Database, href: "/relational" },
  { label: "MongoDB", icon: Boxes },
  { label: "구조 비교", icon: GitCompareArrows },
  { label: "학습 노트", icon: BookOpen },
];

export function Sidebar({ activeLabel }: { activeLabel: string }) {
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
        <span className="phase-kicker">현재 단계</span>
        <strong>{PHASE_LABEL}</strong>
        <p>{CURRENT_PHASE_TITLE}</p>
        <div className="phase-progress">
          <span style={{ width: `${PHASE_PROGRESS_PERCENT}%` }} />
        </div>
        <small>{PHASE_PROGRESS_LABEL}</small>
      </div>
      <div className="sidebar-foot">
        <span className="local-dot" /> localhost 전용
      </div>
    </aside>
  );
}
