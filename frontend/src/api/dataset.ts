import { apiGet, apiPost } from "./client";

export interface StoreCounts {
  customers: number;
  products: number;
  orders: number;
}

export interface StoreResult {
  status: "success" | "failed";
  counts: StoreCounts | null;
  message: string | null;
}

export interface DatasetStatus {
  postgres: StoreResult;
  mongodb: StoreResult;
}

export async function fetchDatasetStatus(): Promise<DatasetStatus> {
  return apiGet<DatasetStatus>("/api/dataset/status");
}

export async function generateDataset(): Promise<DatasetStatus> {
  return apiPost<DatasetStatus>("/api/dataset/generate");
}

export async function resetDataset(): Promise<DatasetStatus> {
  return apiPost<DatasetStatus>("/api/dataset/reset");
}
