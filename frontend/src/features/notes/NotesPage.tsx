import { ArrowUpRight, Database } from "lucide-react";
import { useState } from "react";
import { Sidebar } from "../../components/Sidebar";
import { apiUrl } from "../../api/client";
import { PHASE_FOOTER_LABEL } from "../../config/phase";

interface Note {
  id: string;
  title: string;
  summary: string;
  body: React.ReactNode;
}

const NOTES: Note[] = [
  {
    id: "structure",
    title: "정규화 vs 임베딩",
    summary: "같은 데이터를 테이블로 쪼갤지, 문서 안에 그대로 담을지",
    body: (
      <>
        <p>
          PostgreSQL은 고객·상품·주문을 각자의 테이블로 정규화하고, 주문 내역은
          order_items가 주문과 상품을 잇는 조인으로 표현합니다. 데이터가 한 곳에만
          존재해서 상품명이 바뀌면 모든 주문에 자동으로 반영되지만, 조회할 때는 여러
          테이블을 조인해야 합니다.
        </p>
        <p>
          MongoDB는 주문 시점의 상품명·단가 스냅샷을 주문 문서의 items 배열 안에 그대로
          박아 넣습니다(임베딩). 문서 하나만 읽으면 주문 내역 전체를 알 수 있어 조회가
          빠르지만, 나중에 상품명이 바뀌어도 이미 만들어진 주문의 스냅샷은 갱신되지
          않습니다 — 오히려 "그 시점의 기록"을 보존한다는 점에서는 장점이 되기도 합니다.
        </p>
        <p className="hint-text">
          Phase 5 "구조 비교"에서 같은 주문을 두 구조로 나란히 볼 수 있습니다.
        </p>
      </>
    ),
  },
  {
    id: "syntax",
    title: "SQL vs mongosh 문법 비교",
    summary: "같은 동작을 각 콘솔에서 어떻게 쓰는지",
    body: (
      <div className="results-table-wrap">
        <table className="results-table">
          <thead>
            <tr>
              <th>동작</th>
              <th>PostgreSQL (SQL)</th>
              <th>MongoDB (mongosh)</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>조회</td>
              <td>SELECT * FROM customers WHERE status = &apos;active&apos;;</td>
              <td>db.customers.find({"{"}&quot;status&quot;: &quot;active&quot;{"}"})</td>
            </tr>
            <tr>
              <td>삽입</td>
              <td>INSERT INTO customers (email) VALUES (&apos;a@b.com&apos;);</td>
              <td>db.customers.insertOne({"{"}&quot;email&quot;: &quot;a@b.com&quot;{"}"})</td>
            </tr>
            <tr>
              <td>수정</td>
              <td>UPDATE customers SET full_name = &apos;x&apos; WHERE id = 1;</td>
              <td>db.customers.updateOne({"{...}"}, {"{"}&quot;$set&quot;: {"{...}"}{"}"})</td>
            </tr>
            <tr>
              <td>삭제</td>
              <td>DELETE FROM customers WHERE id = 1;</td>
              <td>db.customers.deleteOne({"{...}"})</td>
            </tr>
            <tr>
              <td>집계</td>
              <td>SELECT status, COUNT(*) FROM orders GROUP BY status;</td>
              <td>db.orders.aggregate([{"{"}&quot;$group&quot;: {"{...}"}{"}"}])</td>
            </tr>
          </tbody>
        </table>
      </div>
    ),
  },
  {
    id: "transactions",
    title: "트랜잭션",
    summary: "BEGIN부터 COMMIT/ROLLBACK까지, 그리고 격리",
    body: (
      <>
        <p>
          트랜잭션은 여러 작업을 하나의 단위로 묶어, 전부 성공하거나 전부 취소되게
          만듭니다. BEGIN으로 시작해서, 작업을 실행한 뒤 COMMIT으로 확정하거나
          ROLLBACK으로 되돌립니다.
        </p>
        <p>
          중요한 점은 <strong>격리(isolation)</strong>입니다: COMMIT하기 전까지는 같은
          트랜잭션 안에서만 변경 사항이 보이고, 다른 연결에서는 여전히 이전 값을 봅니다.
          Phase 6의 트랜잭션 샌드박스에서 "내 트랜잭션에서 본 값"과 "다른 연결에서 본
          값"이 COMMIT 전까지 다르게 나타나는 것이 바로 이 격리입니다.
        </p>
        <p className="hint-text">
          ROLLBACK을 실행하면 트랜잭션 안에서 했던 모든 변경이 없었던 일이 됩니다.
        </p>
      </>
    ),
  },
  {
    id: "indexes",
    title: "인덱스와 실행 계획",
    summary: "인덱스가 항상 빠른 건 아니라는 것",
    body: (
      <>
        <p>
          인덱스는 특정 컬럼으로 행을 빠르게 찾기 위한 별도의 자료구조입니다.
          EXPLAIN ANALYZE로 PostgreSQL이 실제로 어떤 방법(Seq Scan = 테이블 전체를
          순서대로 훑기, Index Scan / Bitmap Heap Scan = 인덱스로 바로 찾아가기)을
          선택했는지 확인할 수 있습니다.
        </p>
        <p>
          <strong>인덱스가 항상 더 빠른 것은 아닙니다.</strong> Phase 6을 만들면서 실제로
          확인한 내용인데, 주문 40건짜리 작은 테이블에서는 인덱스를 만들어도 PostgreSQL이
          여전히 순차 스캔을 선택했습니다 — 테이블 전체가 워낙 작아서 인덱스를 거치는
          비용이 오히려 더 크기 때문입니다. 그래서 인덱스 실습은 10만 행짜리 별도
          테이블로 진행합니다. 실제로 그 규모에서는 인덱스가 생기자 계획이 Seq Scan에서
          Bitmap Heap Scan으로 바뀌고, 실행 시간도 크게 줄어드는 것을 볼 수 있습니다.
        </p>
        <p className="hint-text">
          교훈: 인덱스는 "일단 만들고 보는" 것이 아니라, 테이블 크기와 조회 패턴을 보고
          판단해야 합니다.
        </p>
      </>
    ),
  },
  {
    id: "summary",
    title: "한눈에 비교",
    summary: "PostgreSQL과 MongoDB, 언제 무엇을 쓸까",
    body: (
      <div className="results-table-wrap">
        <table className="results-table">
          <thead>
            <tr>
              <th></th>
              <th>PostgreSQL</th>
              <th>MongoDB</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>데이터 모델</td>
              <td>정규화된 테이블 + 조인</td>
              <td>스키마가 유연한 문서(임베딩)</td>
            </tr>
            <tr>
              <td>강점</td>
              <td>일관성, 복잡한 조인/집계, 정확한 트랜잭션</td>
              <td>빠른 단일 문서 조회, 유연한 구조 변경</td>
            </tr>
            <tr>
              <td>주의할 점</td>
              <td>스키마 변경에 마이그레이션 필요</td>
              <td>비정규화로 인한 데이터 중복/불일치 가능성</td>
            </tr>
          </tbody>
        </table>
      </div>
    ),
  },
];

function NoteCard({ note, open, onToggle }: { note: Note; open: boolean; onToggle: () => void }) {
  return (
    <article className="note-card">
      <button className="note-card-head" onClick={onToggle} aria-expanded={open}>
        <div>
          <h3>{note.title}</h3>
          <p>{note.summary}</p>
        </div>
        <span className="note-card-toggle">{open ? "접기" : "펼치기"}</span>
      </button>
      {open && <div className="note-card-body">{note.body}</div>}
    </article>
  );
}

export function NotesPage() {
  const [openId, setOpenId] = useState<string | null>(NOTES[0].id);

  return (
    <div className="app-shell">
      <Sidebar activeLabel="학습 노트" />

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
              <p className="eyebrow">Reference notes</p>
              <h1 id="page-title">학습 노트</h1>
              <p className="hero-copy">
                Phase 1부터 6까지 실습하며 다룬 핵심 개념을 정리했습니다. 카드를 눌러
                펼쳐보세요.
              </p>
            </div>
          </section>

          <div className="note-list">
            {NOTES.map((note) => (
              <NoteCard
                key={note.id}
                note={note}
                open={openId === note.id}
                onToggle={() => setOpenId((current) => (current === note.id ? null : note.id))}
              />
            ))}
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
