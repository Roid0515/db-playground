import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Database, GitCompareArrows, Layers, Table2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Sidebar } from "../../components/Sidebar";
import { apiUrl } from "../../api/client";
import { OrderComparison, fetchOrderComparison, fetchOrderSummaries } from "../../api/comparison";
import { PHASE_FOOTER_LABEL } from "../../config/phase";

const STATUS_LABEL: Record<string, string> = {
  pending: "대기",
  paid: "결제완료",
  shipped: "배송중",
  cancelled: "취소",
};

function won(cents: number): string {
  return `${cents.toLocaleString()}원`;
}

function RelationalView({ view }: { view: OrderComparison["relational"] }) {
  return (
    <div className="compare-pane">
      <div className="compare-pane-head">
        <Table2 size={16} />
        <span>PostgreSQL · 정규화 테이블 조인</span>
      </div>
      <pre className="document-card compare-sql">{view.sql}</pre>
      <div className="results-table-wrap">
        <table className="results-table">
          <thead>
            <tr>
              <th>고객</th>
              <th>상품</th>
              <th>수량</th>
              <th>단가</th>
            </tr>
          </thead>
          <tbody>
            {view.items.map((item) => (
              <tr key={item.product_id}>
                <td>{view.customer.full_name}</td>
                <td>{item.product_name}</td>
                <td>{item.quantity}</td>
                <td>{won(item.unit_price_cents)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="hint-text compare-note">
        고객 정보와 상품 정보가 각자의 테이블에 정규화되어 있어, 주문 내역을 보려면 customers ·
        order_items · products 세 테이블을 조인해야 합니다. 같은 고객 이름이 행마다 반복해서
        나타나는 것도 정규화 구조의 특징입니다.
      </p>
    </div>
  );
}

function DocumentView({ view }: { view: OrderComparison["document"] }) {
  return (
    <div className="compare-pane">
      <div className="compare-pane-head">
        <Layers size={16} />
        <span>MongoDB · 임베디드 문서</span>
      </div>
      <pre className="document-card">{JSON.stringify(view.document, null, 2)}</pre>
      <p className="hint-text compare-note">
        주문 시점의 상품명·단가 스냅샷이 items 배열 안에 그대로 담겨 있어, 문서 하나만 읽으면
        주문 내역 전체를 알 수 있습니다. 다만 나중에 상품명이 바뀌어도 이미 만들어진 주문
        문서의 스냅샷은 갱신되지 않습니다.
      </p>
    </div>
  );
}

export function ComparisonPage() {
  const [selectedOrder, setSelectedOrder] = useState<number | null>(null);
  const summariesQuery = useQuery({ queryKey: ["comparison-orders"], queryFn: fetchOrderSummaries });

  useEffect(() => {
    if (!selectedOrder && summariesQuery.data && summariesQuery.data.length > 0) {
      setSelectedOrder(summariesQuery.data[0].order_number);
    }
  }, [selectedOrder, summariesQuery.data]);

  const comparisonQuery = useQuery({
    queryKey: ["comparison-order", selectedOrder],
    queryFn: () => fetchOrderComparison(selectedOrder as number),
    enabled: selectedOrder !== null,
  });

  return (
    <div className="app-shell">
      <Sidebar activeLabel="구조 비교" />

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
              <p className="eyebrow">Same data, two structures</p>
              <h1 id="page-title">구조 비교</h1>
              <p className="hero-copy">
                같은 주문을 PostgreSQL의 정규화된 조인 결과와 MongoDB의 임베디드 문서로 나란히
                놓고, 두 구조의 차이를 직접 비교해보세요.
              </p>
            </div>
          </section>

          {summariesQuery.isError && (
            <div className="alert" role="alert">
              주문 목록을 불러오지 못했습니다. 백엔드가 실행 중인지 확인해 주세요.
            </div>
          )}

          {summariesQuery.data && summariesQuery.data.length === 0 && (
            <p className="hint-text">
              비교할 주문이 없습니다. 대시보드에서 샘플 데이터를 먼저 생성해 보세요.
            </p>
          )}

          <div className="relational-layout">
            <aside className="table-list" aria-label="주문 목록">
              <p className="section-kicker">Orders</p>
              {summariesQuery.data?.map((order) => (
                <button
                  key={order.order_number}
                  className={`table-list-item ${selectedOrder === order.order_number ? "active" : ""}`}
                  onClick={() => setSelectedOrder(order.order_number)}
                >
                  <GitCompareArrows size={15} />
                  <span>
                    #{order.order_number} · {order.customer_name}
                  </span>
                  <span className="table-row-count">{STATUS_LABEL[order.status] ?? order.status}</span>
                </button>
              ))}
            </aside>

            <div className="relational-main">
              {comparisonQuery.isLoading && <p className="hint-text">불러오는 중…</p>}
              {comparisonQuery.isError && (
                <div className="alert" role="alert">
                  주문 비교 정보를 불러오지 못했습니다.
                </div>
              )}
              {comparisonQuery.data && (
                <div className="compare-grid">
                  <RelationalView view={comparisonQuery.data.relational} />
                  <DocumentView view={comparisonQuery.data.document} />
                </div>
              )}
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
