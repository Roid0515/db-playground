/** Shared PostgreSQL/MongoDB display metadata, so components stop repeating
 * `type === "postgres" ? ... : ...` for the same handful of labels. */
export type DbType = "postgres" | "mongodb";

interface DbMeta {
  label: string;
  markLetters: string;
  kind: string;
  modelNote: string;
}

export const DB_META: Record<DbType, DbMeta> = {
  postgres: {
    label: "PostgreSQL",
    markLetters: "PG",
    kind: "관계형 데이터베이스",
    modelNote: "정규화 테이블 + 조인",
  },
  mongodb: {
    label: "MongoDB",
    markLetters: "MO",
    kind: "문서형 데이터베이스",
    modelNote: "주문에 상품 스냅샷 내장",
  },
};
