import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, Database, Play, TableProperties, Terminal } from "lucide-react";
import { useEffect, useState } from "react";
import { Sidebar } from "../../components/Sidebar";
import { ApiError, apiUrl } from "../../api/client";
import { QueryResult, fetchTableRows, fetchTables, runQuery } from "../../api/postgres";
import { PHASE_FOOTER_LABEL } from "../../config/phase";

const PAGE_SIZE = 20;

const EXAMPLES: { label: string; sql: string }[] = [
  { label: "SELECT 예시", sql: "SELECT * FROM customers LIMIT 20;" },
  {
    label: "INSERT 예시",
    sql: "INSERT INTO customers (email, full_name) VALUES ('test@example.com', '테스트');",
  },
  {
    label: "UPDATE 예시",
    sql: "UPDATE customers SET full_name = '수정됨' WHERE email = 'test@example.com';",
  },
  { label: "DELETE 예시", sql: "DELETE FROM customers WHERE email = 'test@example.com';" },
];

function ResultsTable({ columns, rows }: { columns: string[]; rows: unknown[][] }) {
  return (
    <div className="results-table-wrap">
      <table className="results-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((value, valueIndex) => (
                <td key={valueIndex}>{value === null ? <span className="null-value">NULL</span> : String(value)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TableBrowser({ tableName }: { tableName: string }) {
  const [page, setPage] = useState(1);

  useEffect(() => {
    setPage(1);
  }, [tableName]);

  const rowsQuery = useQuery({
    queryKey: ["postgres-rows", tableName, page],
    queryFn: () => fetchTableRows(tableName, page, PAGE_SIZE),
  });

  const totalPages = rowsQuery.data ? Math.max(1, Math.ceil(rowsQuery.data.total / PAGE_SIZE)) : 1;

  if (rowsQuery.isLoading) return <p className="hint-text">불러오는 중…</p>;
  if (rowsQuery.isError) return <div className="alert" role="alert">행을 불러오지 못했습니다.</div>;
  if (!rowsQuery.data) return null;

  return (
    <div>
      {rowsQuery.data.rows.length === 0 ? (
        <p className="hint-text">데이터가 없습니다. 대시보드에서 샘플 데이터를 먼저 생성해 보세요.</p>
      ) : (
        <ResultsTable columns={rowsQuery.data.columns} rows={rowsQuery.data.rows} />
      )}
      <div className="pagination">
        <span>
          전체 {rowsQuery.data.total.toLocaleString()}행 · {page} / {totalPages} 페이지
        </span>
        <div className="pagination-buttons">
          <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            이전
          </button>
          <button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
            다음
          </button>
        </div>
      </div>
    </div>
  );
}

function SqlConsole() {
  const [sql, setSql] = useState(EXAMPLES[0].sql);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: runQuery,
    onSuccess: () => {
      // A successful INSERT/UPDATE/DELETE can change what the table browser and
      // dashboard's row counts should show, so make sure they refetch.
      queryClient.invalidateQueries({ queryKey: ["postgres-tables"] });
      queryClient.invalidateQueries({ queryKey: ["postgres-rows"] });
      queryClient.invalidateQueries({ queryKey: ["dataset-status"] });
    },
  });

  const handleRun = () => mutation.mutate(sql);

  return (
    <div>
      <div className="example-row">
        {EXAMPLES.map((example) => (
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
        onKeyDown={(event) => {
          if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
            event.preventDefault();
            handleRun();
          }
        }}
        rows={6}
      />
      <div className="sql-console-actions">
        <span className="hint-text">SELECT · INSERT · UPDATE · DELETE만 실행할 수 있습니다 (⌘/Ctrl+Enter로 실행)</span>
        <button className="refresh-button" onClick={handleRun} disabled={mutation.isPending}>
          <Play size={15} /> 실행
        </button>
      </div>

      {mutation.isError && (
        <div className="alert" role="alert">
          {mutation.error instanceof ApiError ? mutation.error.message : "쿼리를 실행하지 못했습니다."}
        </div>
      )}

      {mutation.data && <QueryResultView result={mutation.data} />}
    </div>
  );
}

function QueryResultView({ result }: { result: QueryResult }) {
  return (
    <div className="query-result">
      <div className="query-meta">
        <span>{result.statement_type}</span>
        <span>{result.duration_ms} ms</span>
        <span>
          {result.columns ? `${result.row_count}행 반환` : `${result.row_count}행 영향받음`}
          {result.truncated && " (최대 개수까지만 표시)"}
        </span>
      </div>
      {result.columns && result.rows && result.rows.length > 0 && (
        <ResultsTable columns={result.columns} rows={result.rows} />
      )}
    </div>
  );
}

export function RelationalPage() {
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"browse" | "sql">("browse");
  const tablesQuery = useQuery({ queryKey: ["postgres-tables"], queryFn: fetchTables });

  useEffect(() => {
    if (!selectedTable && tablesQuery.data && tablesQuery.data.length > 0) {
      setSelectedTable(tablesQuery.data[0].name);
    }
  }, [selectedTable, tablesQuery.data]);

  return (
    <div className="app-shell">
      <Sidebar activeLabel="관계형 DB" />

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
              <p className="eyebrow">Relational database practice</p>
              <h1 id="page-title">관계형 DB 실습</h1>
              <p className="hero-copy">테이블과 행을 살펴보고, SQL을 직접 실행하며 PostgreSQL 구조를 익혀보세요.</p>
            </div>
          </section>

          {tablesQuery.isError && (
            <div className="alert" role="alert">
              테이블 목록을 불러오지 못했습니다. 백엔드가 실행 중인지 확인해 주세요.
            </div>
          )}

          <div className="relational-layout">
            <aside className="table-list" aria-label="테이블 목록">
              <p className="section-kicker">Tables</p>
              {tablesQuery.data?.map((table) => (
                <button
                  key={table.name}
                  className={`table-list-item ${selectedTable === table.name ? "active" : ""}`}
                  onClick={() => {
                    setSelectedTable(table.name);
                    setActiveTab("browse");
                  }}
                >
                  <TableProperties size={15} />
                  <span>{table.name}</span>
                  <span className="table-row-count">{table.row_count}</span>
                </button>
              ))}
            </aside>

            <div className="relational-main">
              <div className="tabs" role="tablist">
                <button
                  role="tab"
                  aria-selected={activeTab === "browse"}
                  className={`tab-button ${activeTab === "browse" ? "active" : ""}`}
                  onClick={() => setActiveTab("browse")}
                >
                  <TableProperties size={15} /> 테이블 탐색
                </button>
                <button
                  role="tab"
                  aria-selected={activeTab === "sql"}
                  className={`tab-button ${activeTab === "sql" ? "active" : ""}`}
                  onClick={() => setActiveTab("sql")}
                >
                  <Terminal size={15} /> SQL 실행
                </button>
              </div>

              <div className="tab-panel">
                {activeTab === "browse" &&
                  (selectedTable ? (
                    <TableBrowser tableName={selectedTable} />
                  ) : (
                    <p className="hint-text">왼쪽에서 테이블을 선택하세요.</p>
                  ))}
                {activeTab === "sql" && <SqlConsole />}
              </div>
            </div>
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
