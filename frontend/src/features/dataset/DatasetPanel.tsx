import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Sparkles, Trash2 } from "lucide-react";
import { DatasetStatus, StoreResult, fetchDatasetStatus, generateDataset, resetDataset } from "../../api/dataset";
import { DB_META, DbType } from "../../config/dbMeta";

function StoreCountCard({ type, result }: { type: DbType; result?: StoreResult }) {
  const { label, markLetters, modelNote } = DB_META[type];
  const failed = result?.status === "failed";

  return (
    <article className={`dataset-card ${type} ${failed ? "failed" : ""}`} aria-label={`${label} 데이터 현황`}>
      <div className="card-topline">
        <div className={`db-mark ${type}`} aria-hidden="true">
          {markLetters}
        </div>
        <span className="dataset-model">{modelNote}</span>
      </div>
      <h3>{label}</h3>
      {failed ? (
        <p className="dataset-error">{result?.message ?? "연결할 수 없습니다."}</p>
      ) : (
        <dl className="dataset-counts">
          <div>
            <dt>고객</dt>
            <dd>{result?.counts?.customers ?? "—"}</dd>
          </div>
          <div>
            <dt>상품</dt>
            <dd>{result?.counts?.products ?? "—"}</dd>
          </div>
          <div>
            <dt>주문</dt>
            <dd>{result?.counts?.orders ?? "—"}</dd>
          </div>
        </dl>
      )}
    </article>
  );
}

function partialFailureMessage(status?: DatasetStatus): string | undefined {
  if (!status) return undefined;
  const failedLabels = (["postgres", "mongodb"] as const)
    .filter((store) => status[store].status === "failed")
    .map((store) => (store === "postgres" ? "PostgreSQL" : "MongoDB"));
  if (failedLabels.length === 0) return undefined;
  return `${failedLabels.join(", ")}에 연결할 수 없어 해당 저장소는 처리되지 않았습니다.`;
}

export function DatasetPanel() {
  const queryClient = useQueryClient();
  const statusQuery = useQuery({ queryKey: ["dataset-status"], queryFn: fetchDatasetStatus });

  const applyResult = (data: DatasetStatus) => queryClient.setQueryData(["dataset-status"], data);
  const generateMutation = useMutation({ mutationFn: generateDataset, onSuccess: applyResult });
  const resetMutation = useMutation({ mutationFn: resetDataset, onSuccess: applyResult });

  const isBusy = generateMutation.isPending || resetMutation.isPending;
  const requestErrorMessage = generateMutation.isError
    ? "샘플 데이터 생성에 실패했습니다."
    : resetMutation.isError
      ? "초기화에 실패했습니다."
      : statusQuery.isError
        ? "데이터 현황을 불러오지 못했습니다."
        : undefined;
  const errorMessage = requestErrorMessage ?? partialFailureMessage(statusQuery.data);

  return (
    <section className="dataset-section" aria-labelledby="dataset-title">
      <div className="section-title-row">
        <div>
          <p className="section-kicker">Sample data</p>
          <h2 id="dataset-title">온라인 쇼핑몰 샘플 데이터</h2>
        </div>
        <div className="dataset-actions">
          <button className="ghost-button" onClick={() => resetMutation.mutate()} disabled={isBusy}>
            <Trash2 size={15} /> 초기화
          </button>
          <button className="refresh-button" onClick={() => generateMutation.mutate()} disabled={isBusy}>
            <Sparkles size={16} className={isBusy ? "spinning" : ""} /> 샘플 데이터 생성
          </button>
        </div>
      </div>

      {errorMessage && (
        <div className="alert" role="alert">
          {errorMessage}
        </div>
      )}

      <p className="dataset-copy">
        고객 24 · 상품 18 · 주문 40건을 매번 같은 시드로 생성합니다. PostgreSQL은 주문 내역을 <code>order_items</code>{" "}
        테이블과의 조인으로 보여주고, MongoDB는 같은 내역을 주문 문서 안의 <code>items</code> 배열에 그대로 담습니다.
      </p>

      <div className="dataset-grid">
        <StoreCountCard type="postgres" result={statusQuery.data?.postgres} />
        <StoreCountCard type="mongodb" result={statusQuery.data?.mongodb} />
      </div>
    </section>
  );
}
