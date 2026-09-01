import { apiGet, apiPost } from "./client";

export interface IndexStatus {
  table: string;
  column: string;
  index_name: string;
  index_exists: boolean;
  row_count: number;
}

export interface ExplainResult {
  node_type: string;
  used_index: boolean;
  execution_time_ms: number;
  planning_time_ms: number;
  row_count: number;
  plan_text: string;
}

export async function fetchIndexStatus(): Promise<IndexStatus> {
  return apiGet<IndexStatus>("/api/index-lab/status");
}

export async function explainQuery(): Promise<ExplainResult> {
  return apiPost<ExplainResult>("/api/index-lab/explain");
}

export async function createDemoIndex(): Promise<IndexStatus> {
  return apiPost<IndexStatus>("/api/index-lab/create-index");
}

export async function dropDemoIndex(): Promise<IndexStatus> {
  return apiPost<IndexStatus>("/api/index-lab/drop-index");
}
