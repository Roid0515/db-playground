export interface ColumnInfo {
  name: string;
  type: string;
}

export interface TableInfo {
  name: string;
  row_count: number;
  columns: ColumnInfo[];
}

export interface TableRows {
  columns: string[];
  rows: unknown[][];
  total: number;
  page: number;
  page_size: number;
}

export interface QueryResult {
  columns: string[] | null;
  rows: unknown[][] | null;
  row_count: number;
  truncated: boolean;
  duration_ms: number;
  statement_type: string;
}

export class ApiError extends Error {}

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function parseOrThrow<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(body?.detail ?? "요청을 처리하지 못했습니다.");
  }
  return response.json() as Promise<T>;
}

export async function fetchTables(): Promise<TableInfo[]> {
  const response = await fetch(`${API_URL}/api/postgres/tables`);
  return parseOrThrow(response);
}

export async function fetchTableRows(
  tableName: string,
  page: number,
  pageSize: number,
): Promise<TableRows> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  const response = await fetch(`${API_URL}/api/postgres/tables/${encodeURIComponent(tableName)}/rows?${params}`);
  return parseOrThrow(response);
}

export async function runQuery(sql: string): Promise<QueryResult> {
  const response = await fetch(`${API_URL}/api/postgres/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sql }),
  });
  return parseOrThrow(response);
}
