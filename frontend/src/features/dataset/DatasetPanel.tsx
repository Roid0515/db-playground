import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Sparkles, Trash2 } from "lucide-react";
import { DatasetStatus, StoreCounts, fetchDatasetStatus, generateDataset, resetDataset } from "../../api/dataset";

function StoreCountCard({ type, counts }: { type: "postgres" | "mongodb"; counts?: StoreCounts }) {
  const label = type === "postgres" ? "PostgreSQL" : "MongoDB";
  const description = type === "postgres" ? "정규화 테이블 + 조인" : "주문에 상품 스냅샷 내장";

  return (
    <article className={`dataset-card ${type}`} aria-label={`${label} 데이터 현황`}>
      <div className="card-topline">
        <div className={`db-mark ${type}`} aria-hidden="true">{type === "postgres" ? "PG" : "MO"}</div>
        <span className="dataset-model">{description}</span>
      </div>
      <h3>{label}</h3>
      <dl className="dataset-counts">
        <div>
          <dt>고객</dt>
          <dd>{counts?.customers ?? "—"}</dd>
        </div>
        <div>
          <dt>상품</dt>
          <dd>{counts?.products ?? "—"}</dd>
        </div>
        <div>
          <dt>주문</dt>
          <dd>{counts?.orders ?? "—"}</dd>
        </div>
      </dl>
    </article>
  );
}

export function DatasetPanel() {
  const queryClient = useQueryClient();
  const statusQuery = useQuery({ queryKey: ["dataset-status"], queryFn: fetchDatasetStatus });

  const applyResult = (data: DatasetStatus) => queryClient.setQueryData(["dataset-status"], data);
  const generateMutation = useMutation({ mutationFn: generateDataset, onSuccess: applyResult });
  const resetMutation = useMutation({ mutationFn: resetDataset, onSuccess: applyResult });

  const isBusy = generateMutation.isPending || resetMutation.isPending;
  const errorMessage = generateMutation.isError
    ? "샘플 데이터 생성에 실패했습니다."
    : resetMutation.isError
      ? "초기화에 실패했습니다."
      : statusQuery.isError
        ? "데이터 현황을 불러오지 못했습니다."
        : undefined;

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
        <StoreCountCard type="postgres" counts={statusQuery.data?.postgres} />
        <StoreCountCard type="mongodb" counts={statusQuery.data?.mongodb} />
      </div>
    </section>
  );
}
