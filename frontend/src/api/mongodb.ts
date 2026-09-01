import { apiGet, apiPost } from "./client";

export interface CollectionInfo {
  name: string;
  document_count: number;
  sample_fields: string[];
}

export interface CollectionDocuments {
  documents: Record<string, unknown>[];
  total: number;
  page: number;
  page_size: number;
}

export interface MongoQueryResult {
  documents: Record<string, unknown>[] | null;
  row_count: number;
  truncated: boolean;
  duration_ms: number;
  operation: string;
}

export async function fetchCollections(): Promise<CollectionInfo[]> {
  return apiGet<CollectionInfo[]>("/api/mongodb/collections");
}

export async function fetchCollectionDocuments(
  collectionName: string,
  page: number,
  pageSize: number,
): Promise<CollectionDocuments> {
  return apiGet<CollectionDocuments>(
    `/api/mongodb/collections/${encodeURIComponent(collectionName)}/documents`,
    { page, page_size: pageSize },
  );
}

export async function runCommand(command: string): Promise<MongoQueryResult> {
  return apiPost<MongoQueryResult>("/api/mongodb/query", { command });
}
