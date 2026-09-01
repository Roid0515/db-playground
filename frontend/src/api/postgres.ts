import { apiGet, apiPost } from "./client";

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

export async function fetchTables(): Promise<TableInfo[]> {
  return apiGet<TableInfo[]>("/api/postgres/tables");
}

export async function fetchTableRows(
  tableName: string,
  page: number,
  pageSize: number,
): Promise<TableRows> {
  return apiGet<TableRows>(`/api/postgres/tables/${encodeURIComponent(tableName)}/rows`, {
    page,
    page_size: pageSize,
  });
}

export async function runQuery(sql: string): Promise<QueryResult> {
  return apiPost<QueryResult>("/api/postgres/query", { sql });
}
