import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, CircleCheck, Database, RefreshCw, Server, Timer } from "lucide-react";
import { Link } from "react-router-dom";
import { Sidebar } from "../../components/Sidebar";
import { apiUrl } from "../../api/client";
import { fetchSystemHealth, ServiceHealth } from "../../api/health";
import { DB_META, DbType } from "../../config/dbMeta";
import { CURRENT_PHASE_TITLE, PHASE_FOOTER_LABEL, PHASE_LABEL } from "../../config/phase";
import { DatasetPanel } from "../dataset/DatasetPanel";

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
              <span>지금까지 실습한 핵심 개념을 학습 노트에서 정리해보세요.</span>
            </div>
            <Link className="cta-link" to="/notes">
              학습 노트 보기 <ArrowUpRight size={15} />
            </Link>
          </section>

          <section className="ready-panel">
            <div className="ready-icon">
              <CircleCheck size={24} />
            </div>
            <div>
              <p>All phases complete</p>
              <h2>7단계 학습을 모두 마쳤습니다.</h2>
              <span>
                관계형 DB 실습, MongoDB 실습, 구조 비교, 트랜잭션·인덱스까지 모두
                둘러봤습니다. 사이드바에서 언제든 다시 돌아가 실습할 수 있습니다.
              </span>
            </div>
          </section>
        </div>
        <footer><span>DB Playground · Local learning environment</span><span>{PHASE_FOOTER_LABEL}</span></footer>
      </main>
    </div>
  );
}