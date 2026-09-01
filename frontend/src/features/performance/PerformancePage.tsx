import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowUpRight,
  Database,
  Gauge,
  Play,
  RefreshCw,
  Terminal,
  Zap,
} from "lucide-react";
import { useState } from "react";
import { Sidebar } from "../../components/Sidebar";
import { ApiError, apiUrl } from "../../api/client";
import {
  ExplainResult,
  createDemoIndex,
  dropDemoIndex,
  explainQuery,
  fetchIndexStatus,
} from "../../api/indexLab";
import {
  ExecuteResult,
  beginTransaction,
  commitTransaction,
  executeInTransaction,
  peekCommittedState,
  peekWithinTransaction,
  rollbackTransaction,
} from "../../api/transactionLab";
import { PHASE_FOOTER_LABEL } from "../../config/phase";

const TXN_EXAMPLES: { label: string; sql: string }[] = [
  {
    label: "재고 차감 (UPDATE)",
    sql: "UPDATE products SET stock_quantity = stock_quantity - 1 WHERE id = (SELECT id FROM products ORDER BY id LIMIT 1);",
  },
  {
    label: "재고 확인 (SELECT)",
    sql: "SELECT id, name, stock_quantity FROM products ORDER BY id LIMIT 5;",
  },
];

function ResultsTable({ result }: { result: ExecuteResult }) {
  if (!result.columns || !result.rows) {
    return <p className="hint-text">{result.row_count}행 영향받음</p>;
  }
  return (
    <div className="results-table-wrap">
      <table className="results-table">
        <thead>
          <tr>
            {result.columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {result.rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((value, valueIndex) => (
                <td key={valueIndex}>{String(value)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function IndexLabPanel() {
  const queryClient = useQueryClient();
  const [history, setHistory] = useState<ExplainResult[]>([]);
  const statusQuery = useQuery({ queryKey: ["index-lab-status"], queryFn: fetchIndexStatus });

  const explainMutation = useMutation({
    mutationFn: explainQuery,
    onSuccess: (result) => setHistory((prev) => [result, ...prev].slice(0, 2)),
  });
  const createMutation = useMutation({
    mutationFn: createDemoIndex,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["index-lab-status"] }),
  });
  const dropMutation = useMutation({
    mutationFn: dropDemoIndex,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["index-lab-status"] }),
  });

  const status = statusQuery.data;

  return (
    <div>
      <p className="hint-text compare-note">
        인덱스 실습은 쇼핑몰 샘플 데이터가 아니라, 이 실습만을 위해 만든 별도의 테이블(
        index_lab_events, {status ? status.row_count.toLocaleString() : "…"}행)에서 진행됩니다.
        주문 40건짜리 테이블은 너무 작아서 인덱스를 만들어도 PostgreSQL이 여전히 순차 스캔을
        더 빠르다고 판단하기 때문입니다.
      </p>

      <div className="index-lab-status">
        <span className="hint-text">
          대상: <code>{status?.table}.{status?.column}</code>
        </span>
        <span className={`status-chip ${status?.index_exists ? "healthy" : "offline"}`}>
          <span className="status-dot" />
          {status?.index_exists ? "인덱스 있음" : "인덱스 없음"}
        </span>
      </div>

      <div className="index-lab-actions">
        <button
          className="refresh-button"
          onClick={() => explainMutation.mutate()}
          disabled={explainMutation.isPending}
        >
          <Play size={15} /> EXPLAIN ANALYZE 실행
        </button>
        <button
          className="ghost-button"
          onClick={() => createMutation.mutate()}
          disabled={createMutation.isPending || status?.index_exists}
        >
          인덱스 생성
        </button>
        <button
          className="ghost-button"
          onClick={() => dropMutation.mutate()}
          disabled={dropMutation.isPending || !status?.index_exists}
        >
          인덱스 삭제
        </button>
      </div>

      {explainMutation.isError && (
        <div className="alert" role="alert">
          {explainMutation.error instanceof ApiError
            ? explainMutation.error.message
            : "실행 계획을 가져오지 못했습니다."}
        </div>
      )}

      {history.length > 0 && (
        <div className="compare-grid index-lab-history">
          {history.map((result, index) => (
            <div className="compare-pane" key={index}>
              <div className="compare-pane-head">
                <Gauge size={16} />
                <span>{index === 0 ? "최근 실행" : "이전 실행"}</span>
              </div>
              <div className="query-meta">
                <span>{result.node_type}</span>
                <span>{result.used_index ? "인덱스 사용" : "순차 스캔"}</span>
                <span>{result.execution_time_ms} ms</span>
                <span>{result.row_count}행</span>
              </div>
              <pre className="document-card compare-sql">{result.plan_text}</pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function TransactionLabPanel() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sql, setSql] = useState(TXN_EXAMPLES[0].sql);
  const [withinResult, setWithinResult] = useState<ExecuteResult | null>(null);
  const [executeError, setExecuteError] = useState<string | null>(null);

  const committedQuery = useQuery({
    queryKey: ["txn-lab-committed", sessionId],
    queryFn: peekCommittedState,
  });

  const beginMutation = useMutation({
    mutationFn: beginTransaction,
    onSuccess: async ({ session_id }) => {
      setSessionId(session_id);
      setWithinResult(await peekWithinTransaction(session_id));
    },
  });

  const executeMutation = useMutation({
    mutationFn: () => executeInTransaction(sessionId as string, sql),
    onSuccess: async () => {
      setExecuteError(null);
      setWithinResult(await peekWithinTransaction(sessionId as string));
    },
    onError: (error) => {
      setExecuteError(error instanceof ApiError ? error.message : "실행하지 못했습니다.");
    },
  });

  const endTransaction = async (action: (id: string) => Promise<{ status: string }>) => {
    if (!sessionId) return;
    await action(sessionId);
    setSessionId(null);
    setWithinResult(null);
    await committedQuery.refetch();
  };

  const commitMutation = useMutation({ mutationFn: () => endTransaction(commitTransaction) });
  const rollbackMutation = useMutation({ mutationFn: () => endTransaction(rollbackTransaction) });

  return (
    <div>
      <p className="hint-text compare-note">
        products 테이블의 재고를 예시로, 트랜잭션이 COMMIT 되기 전까지는 다른 연결에서 그
        변경이 보이지 않는다는 것을 직접 확인해보세요.
      </p>

      {!sessionId ? (
        <button
          className="refresh-button"
          onClick={() => beginMutation.mutate()}
          disabled={beginMutation.isPending}
        >
          <Terminal size={15} /> BEGIN 시작
        </button>
      ) : (
        <div>
          <div className="example-row">
            {TXN_EXAMPLES.map((example) => (
              <button key={example.label} className="ghost-button" onClick={() => setSql(example.sql)}>
                {example.label}
              </button>
            ))}
          </div>
          <textarea
            className="sql-editor"
            value={sql}
            spellCheck={false}
            onChange={(event) => setSql(event.target.value)}
            rows={4}
          />
          <div className="sql-console-actions">
            <span className="hint-text">SELECT · INSERT · UPDATE · DELETE만 실행할 수 있습니다</span>
            <button
              className="refresh-button"
              onClick={() => executeMutation.mutate()}
              disabled={executeMutation.isPending}
            >
              <Play size={15} /> 트랜잭션 내에서 실행
            </button>
          </div>
          {executeError && (
            <div className="alert" role="alert">
              {executeError}
            </div>
          )}

          <div className="txn-lab-buttons">
            <button
              className="refresh-button"
              onClick={() => commitMutation.mutate()}
              disabled={commitMutation.isPending}
            >
              COMMIT
            </button>
            <button
              className="ghost-button"
              onClick={() => rollbackMutation.mutate()}
              disabled={rollbackMutation.isPending}
            >
              ROLLBACK
            </button>
          </div>
        </div>
      )}

      <div className="compare-grid txn-lab-panes">
        <div className="compare-pane">
          <div className="compare-pane-head">
            <Terminal size={16} />
            <span>내 트랜잭션에서 본 값 {!sessionId && "(트랜잭션 없음)"}</span>
          </div>
          {withinResult ? <ResultsTable result={withinResult} /> : <p className="hint-text">-</p>}
        </div>
        <div className="compare-pane">
          <div className="compare-pane-head">
            <Database size={16} />
            <span>다른 연결에서 본 값 (커밋된 상태)</span>
            <button
              className="ghost-button txn-lab-refresh"
              onClick={() => committedQuery.refetch()}
              aria-label="새로고침"
            >
              <RefreshCw size={13} />
            </button>
          </div>
          {committedQuery.data ? (
            <ResultsTable result={committedQuery.data} />
          ) : (
            <p className="hint-text">불러오는 중…</p>
          )}
        </div>
      </div>
    </div>
  );
}

export function PerformancePage() {
  const [activeTab, setActiveTab] = useState<"index" | "transaction">("index");

  return (
    <div className="app-shell">
      <Sidebar activeLabel="트랜잭션 · 인덱스" />

      <main>
        <header className="topbar">
          <div className="mobile-brand">
            <Database size={18} /> DB Playground
          </div>
          <div className="environment">
            <span /> Development
          </div>
          <a href={apiUrl("/docs")} target="_blank" rel="noreferrer">
            API 문서 <ArrowUpRight size={14} />
          </a>
        </header>

        <div className="content">
          <section className="hero" aria-labelledby="page-title">
            <div>
              <p className="eyebrow">Concurrency and query performance</p>
              <h1 id="page-title">트랜잭션 · 인덱스</h1>
              <p className="hero-copy">
                실행 계획으로 인덱스의 효과를 확인하고, 트랜잭션 샌드박스로 COMMIT 전후의
                격리 동작을 직접 실습해보세요.
              </p>
            </div>
          </section>

          <div className="tabs" role="tablist">
            <button
              role="tab"
              aria-selected={activeTab === "index"}
              className={`tab-button ${activeTab === "index" ? "active" : ""}`}
              onClick={() => setActiveTab("index")}
            >
              <Gauge size={15} /> 인덱스 실습
            </button>
            <button
              role="tab"
              aria-selected={activeTab === "transaction"}
              className={`tab-button ${activeTab === "transaction" ? "active" : ""}`}
              onClick={() => setActiveTab("transaction")}
            >
              <Zap size={15} /> 트랜잭션 실습
            </button>
          </div>
          <div className="tab-panel">
            {activeTab === "index" && <IndexLabPanel />}
            {activeTab === "transaction" && <TransactionLabPanel />}
          </div>
        </div>
        <footer>
          <span>DB Playground · Local learning environment</span>
          <span>{PHASE_FOOTER_LABEL}</span>
        </footer>
      </main>
    </div>
  );
}
