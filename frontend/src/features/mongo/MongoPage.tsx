import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, Boxes, Database, Play, Terminal } from "lucide-react";
import { useEffect, useState } from "react";
import { Sidebar } from "../../components/Sidebar";
import { ApiError, apiUrl } from "../../api/client";
import {
  MongoQueryResult,
  fetchCollectionDocuments,
  fetchCollections,
  runCommand,
} from "../../api/mongodb";
import { PHASE_FOOTER_LABEL } from "../../config/phase";

const PAGE_SIZE = 20;

const EXAMPLES: { label: string; command: string }[] = [
  { label: "find 예시", command: 'db.customers.find({"status": "active"})' },
  {
    label: "aggregate 예시",
    command:
      'db.orders.aggregate([{"$group": {"_id": "$status", "count": {"$sum": 1}}}])',
  },
  {
    label: "insertOne 예시",
    command: 'db.customers.insertOne({"email": "test@example.com", "full_name": "테스트"})',
  },
  {
    label: "updateOne 예시",
    command:
      'db.customers.updateOne({"email": "test@example.com"}, {"$set": {"full_name": "수정됨"}})',
  },
  {
    label: "deleteOne 예시",
    command: 'db.customers.deleteOne({"email": "test@example.com"})',
  },
];

function DocumentList({ documents }: { documents: Record<string, unknown>[] }) {
  return (
    <div className="document-list">
      {documents.map((doc, index) => (
        <pre className="document-card" key={(doc._id as string) ?? index}>
          {JSON.stringify(doc, null, 2)}
        </pre>
      ))}
    </div>
  );
}

function CollectionBrowser({ collectionName }: { collectionName: string }) {
  const [page, setPage] = useState(1);

  useEffect(() => {
    setPage(1);
  }, [collectionName]);

  const documentsQuery = useQuery({
    queryKey: ["mongo-documents", collectionName, page],
    queryFn: () => fetchCollectionDocuments(collectionName, page, PAGE_SIZE),
  });

  const totalPages = documentsQuery.data
    ? Math.max(1, Math.ceil(documentsQuery.data.total / PAGE_SIZE))
    : 1;

  if (documentsQuery.isLoading) return <p className="hint-text">불러오는 중…</p>;
  if (documentsQuery.isError)
    return (
      <div className="alert" role="alert">
        문서를 불러오지 못했습니다.
      </div>
    );
  if (!documentsQuery.data) return null;

  return (
    <div>
      {documentsQuery.data.documents.length === 0 ? (
        <p className="hint-text">데이터가 없습니다. 대시보드에서 샘플 데이터를 먼저 생성해 보세요.</p>
      ) : (
        <DocumentList documents={documentsQuery.data.documents} />
      )}
      <div className="pagination">
        <span>
          전체 {documentsQuery.data.total.toLocaleString()}건 · {page} / {totalPages} 페이지
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

function MongoConsole() {
  const [command, setCommand] = useState(EXAMPLES[0].command);
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: runCommand,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mongo-collections"] });
      queryClient.invalidateQueries({ queryKey: ["mongo-documents"] });
      queryClient.invalidateQueries({ queryKey: ["dataset-status"] });
    },
  });

  const handleRun = () => mutation.mutate(command);

  return (
    <div>
      <div className="example-row">
        {EXAMPLES.map((example) => (
          <button
            key={example.label}
            className="ghost-button"
            onClick={() => setCommand(example.command)}
          >
            {example.label}
          </button>
        ))}
      </div>
      <textarea
        className="sql-editor"
        value={command}
        spellCheck={false}
        onChange={(event) => setCommand(event.target.value)}
        onKeyDown={(event) => {
          if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
            event.preventDefault();
            handleRun();
          }
        }}
        rows={6}
      />
      <div className="sql-console-actions">
        <span className="hint-text">
          find · aggregate · countDocuments · insertOne/Many · updateOne/Many ·
          deleteOne/Many만 실행할 수 있습니다 (⌘/Ctrl+Enter로 실행)
        </span>
        <button className="refresh-button" onClick={handleRun} disabled={mutation.isPending}>
          <Play size={15} /> 실행
        </button>
      </div>

      {mutation.isError && (
        <div className="alert" role="alert">
          {mutation.error instanceof ApiError ? mutation.error.message : "명령을 실행하지 못했습니다."}
        </div>
      )}

      {mutation.data && <QueryResultView result={mutation.data} />}
    </div>
  );
}

function QueryResultView({ result }: { result: MongoQueryResult }) {
  return (
    <div className="query-result">
      <div className="query-meta">
        <span>{result.operation}</span>
        <span>{result.duration_ms} ms</span>
        <span>
          {result.documents ? `${result.row_count}건 반환` : `${result.row_count}건 영향받음`}
          {result.truncated && " (최대 개수까지만 표시)"}
        </span>
      </div>
      {result.documents && result.documents.length > 0 && (
        <DocumentList documents={result.documents} />
      )}
    </div>
  );
}

export function MongoPage() {
  const [selectedCollection, setSelectedCollection] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"browse" | "console">("browse");
  const collectionsQuery = useQuery({ queryKey: ["mongo-collections"], queryFn: fetchCollections });

  useEffect(() => {
    if (!selectedCollection && collectionsQuery.data && collectionsQuery.data.length > 0) {
      setSelectedCollection(collectionsQuery.data[0].name);
    }
  }, [selectedCollection, collectionsQuery.data]);

  return (
    <div className="app-shell">
      <Sidebar activeLabel="MongoDB" />

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
              <p className="eyebrow">Document database practice</p>
              <h1 id="page-title">MongoDB 실습</h1>
              <p className="hero-copy">
                컬렉션과 문서를 살펴보고, mongosh 스타일 명령을 직접 실행하며 MongoDB 구조를
                익혀보세요.
              </p>
            </div>
          </section>

          {collectionsQuery.isError && (
            <div className="alert" role="alert">
              컬렉션 목록을 불러오지 못했습니다. 백엔드가 실행 중인지 확인해 주세요.
            </div>
          )}

          <div className="relational-layout">
            <aside className="table-list" aria-label="컬렉션 목록">
              <p className="section-kicker">Collections</p>
              {collectionsQuery.data?.map((collection) => (
                <button
                  key={collection.name}
                  className={`table-list-item ${selectedCollection === collection.name ? "active" : ""}`}
                  onClick={() => {
                    setSelectedCollection(collection.name);
                    setActiveTab("browse");
                  }}
                >
                  <Boxes size={15} />
                  <span>{collection.name}</span>
                  <span className="table-row-count">{collection.document_count}</span>
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
                  <Boxes size={15} /> 문서 탐색
                </button>
                <button
                  role="tab"
                  aria-selected={activeTab === "console"}
                  className={`tab-button ${activeTab === "console" ? "active" : ""}`}
                  onClick={() => setActiveTab("console")}
                >
                  <Terminal size={15} /> 명령 실행
                </button>
              </div>

              <div className="tab-panel">
                {activeTab === "browse" &&
                  (selectedCollection ? (
                    <CollectionBrowser collectionName={selectedCollection} />
                  ) : (
                    <p className="hint-text">왼쪽에서 컬렉션을 선택하세요.</p>
                  ))}
                {activeTab === "console" && <MongoConsole />}
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
