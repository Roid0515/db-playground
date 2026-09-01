import { apiGet, apiPost } from "./client";

export interface ExecuteResult {
  columns: string[] | null;
  rows: unknown[][] | null;
  row_count: number;
}

export async function beginTransaction(): Promise<{ session_id: string }> {
  return apiPost<{ session_id: string }>("/api/transaction-lab/begin");
}

export async function executeInTransaction(sessionId: string, sql: string): Promise<ExecuteResult> {
  return apiPost<ExecuteResult>("/api/transaction-lab/execute", { session_id: sessionId, sql });
}

export async function peekWithinTransaction(sessionId: string): Promise<ExecuteResult> {
  return apiPost<ExecuteResult>("/api/transaction-lab/peek", { session_id: sessionId });
}

export async function peekCommittedState(): Promise<ExecuteResult> {
  return apiGet<ExecuteResult>("/api/transaction-lab/peek-committed");
}

export async function commitTransaction(sessionId: string): Promise<{ status: string }> {
  return apiPost<{ status: string }>("/api/transaction-lab/commit", { session_id: sessionId });
}

export async function rollbackTransaction(sessionId: string): Promise<{ status: string }> {
  return apiPost<{ status: string }>("/api/transaction-lab/rollback", { session_id: sessionId });
}
