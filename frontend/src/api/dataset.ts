export interface StoreCounts {
  customers: number;
  products: number;
  orders: number;
}

export interface DatasetStatus {
  postgres: StoreCounts;
  mongodb: StoreCounts;
}

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function parseOrThrow(response: Response): Promise<DatasetStatus> {
  if (!response.ok) throw new Error("샘플 데이터 요청을 처리하지 못했습니다.");
  return response.json() as Promise<DatasetStatus>;
}

export async function fetchDatasetStatus(): Promise<DatasetStatus> {
  const response = await fetch(`${API_URL}/api/dataset/status`);
  return parseOrThrow(response);
}

export async function generateDataset(): Promise<DatasetStatus> {
  const response = await fetch(`${API_URL}/api/dataset/generate`, { method: "POST" });
  return parseOrThrow(response);
}

export async function resetDataset(): Promise<DatasetStatus> {
  const response = await fetch(`${API_URL}/api/dataset/reset`, { method: "POST" });
  return parseOrThrow(response);
}
