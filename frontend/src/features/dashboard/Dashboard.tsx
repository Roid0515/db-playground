import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, CircleCheck, Database, LockKeyhole, RefreshCw, Server, Timer } from "lucide-react";
import { Link } from "react-router-dom";
import { Sidebar } from "../../components/Sidebar";
import { apiUrl } from "../../api/client";
import { fetchSystemHealth, ServiceHealth } from "../../api/health";
import { DB_META, DbType } from "../../config/dbMeta";
import {
  CURRENT_PHASE_TITLE,
  PHASE_FOOTER_LABEL,
  PHASE_LABEL,
  PHASE_SCOPE_NOTE,
} from "../../config/phase";
import { DatasetPanel } from "../dataset/DatasetPanel";

const nextSteps = [
  { number: "04", title: "MongoDB 실습", copy: "문서 구조와 필터, 집계 파이프라인을 익힙니다." },
  { number: "05", title: "구조 비교", copy: "같은 데이터를 두 구조로 나란히 놓고 차이를 짚어봅니다." },
  { number: "06", title: "트랜잭션 · 인덱스", copy: "동시성과 조회 성능을 실습으로 이해합니다." },
];

function formatTime(value?: string) {
  if (!value) return "확인 중";
  return new Intl.DateTimeFormat("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function StatusCard({ health, loading, type }: { health?: ServiceHealth; loading: boolean; type: DbType }) {
  const healthy = health?.status === "healthy";
  const { label, kind: description, markLetters } = DB_META[type];

  return (
    <article className={`status-card ${type}`} aria-label={`${label} 연결 상태`}>
      <div className="card-topline">
        <div className={`db-mark ${type}`} aria-hidden="true">{markLetters}</div>
        <span className={`status-chip ${healthy ? "healthy" : "offline"}`}>
          <span className="status-dot" />
          {loading ? "확인 중" : healthy ? "정상 연결" : "연결 안 됨"}
        </span>
      </div>
      <div className="card-heading">
        <p>{description}</p>
        <h2>{label}</h2>
      </div>
      <dl className="metrics">
        <div>
          <dt><Timer size={15} /> 응답 시간</dt>
          <dd>{health ? `${health.latency_ms} ms` : "—"}</dd>
        </div>
        <div>
          <dt><Server size={15} /> 버전</dt>
          <dd>{health?.version ?? "—"}</dd>
        </div>
      </dl>
      <div className="card-foot">
        <span>마지막 확인 {formatTime(health?.checked_at)}</span>
        <span className="detail-link">상세 보기 <ArrowUpRight size={15} /></span>
      </div>
    </article>
  );
}

export function Dashboard() {
  const healthQuery = useQuery({
    queryKey: ["system-health"],
    queryFn: fetchSystemHealth,
    refetchInterval: 15_000,
  });
  const allHealthy = healthQuery.data?.status === "healthy";

  return (
    <div className="app-shell">
      <Sidebar activeLabel="대시보드" />

      <main>
        <header className="topbar">
          <div className="mobile-brand"><Database size={18} /> DB Playground</div>
          <div className="environment"><span /> Development</div>
          <a href={apiUrl("/docs")} target="_blank" rel="noreferrer">API 문서 <ArrowUpRight size={14} /></a>
        </header>

        <div className="content">
          <section className="hero" aria-labelledby="page-title">
            <div>
              <p className="eyebrow">Database learning workspace</p>
              <h1 id="page-title">두 데이터베이스,<br />하나의 놀이터.</h1>
              <p className="hero-copy">관계형 구조와 문서형 구조를 나란히 살펴보며 데이터가 연결되고 저장되는 방식을 직접 익혀보세요.</p>
            </div>
            <button className="refresh-button" onClick={() => void healthQuery.refetch()} disabled={healthQuery.isFetching}>
              <RefreshCw size={17} className={healthQuery.isFetching ? "spinning" : ""} />
              상태 새로고침
            </button>
          </section>

          {healthQuery.isError && (
            <div className="alert" role="alert">
              백엔드 상태를 불러올 수 없습니다. API가 실행 중인지 확인한 뒤 다시 시도해 주세요.
            </div>
          )}

          <section className="status-section" aria-labelledby="status-title">
            <div className="section-title-row">
              <div>
                <p className="section-kicker">System status</p>
                <h2 id="status-title">연결 상태</h2>
              </div>
              <span className={`overall ${allHealthy ? "healthy" : "checking"}`}>
                {allHealthy ? "모든 시스템 정상" : healthQuery.isLoading ? "시스템 확인 중" : "확인이 필요합니다"}
              </span>
            </div>
            <div className="status-grid">
              <StatusCard type="postgres" health={healthQuery.data?.services.postgres} loading={healthQuery.isLoading} />
              <StatusCard type="mongodb" health={healthQuery.data?.services.mongodb} loading={healthQuery.isLoading} />
            </div>
          </section>

          <section className="ready-panel">
            <div className="ready-icon"><CircleCheck size={24} /></div>
            <div>
              <p>Foundation ready</p>
              <h2>{allHealthy ? "실습 환경이 준비되었습니다." : "기반 구성이 완료되었습니다."}</h2>
              <span>{allHealthy ? "두 데이터베이스가 응답하고 있습니다. 아래에서 같은 데이터를 서로 다른 구조로 만나보세요." : "데이터베이스가 시작되면 상태가 자동으로 갱신됩니다. 15초마다 다시 확인합니다."}</span>
            </div>
          </section>

          <DatasetPanel />

          <section className="cta-panel">
            <div>
              <p className="section-kicker">{PHASE_LABEL}</p>
              <h2>{CURRENT_PHASE_TITLE}</h2>
              <span>방금 생성한 샘플 데이터를 테이블별로 살펴보고, SQL을 직접 실행해보세요.</span>
            </div>
            <Link className="cta-link" to="/relational">
              테이블 탐색하기 <ArrowUpRight size={15} />
            </Link>
          </section>

          <section className="roadmap" aria-labelledby="roadmap-title">
            <div className="section-title-row">
              <div>
                <p className="section-kicker">Coming next</p>
                <h2 id="roadmap-title">다음 학습 단계</h2>
              </div>
              <span className="scope-note">{PHASE_SCOPE_NOTE}</span>
            </div>
            <div className="roadmap-grid">
              {nextSteps.map((step) => (
                <article key={step.number}>
                  <span className="step-number">{step.number}</span>
                  <LockKeyhole size={16} />
                  <h3>{step.title}</h3>
                  <p>{step.copy}</p>
                </article>
              ))}
            </div>
          </section>
        </div>
        <footer><span>DB Playground · Local learning environment</span><span>{PHASE_FOOTER_LABEL}</span></footer>
      </main>
    </div>
  );
}