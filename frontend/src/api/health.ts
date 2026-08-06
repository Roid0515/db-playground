export type ServiceStatus = "healthy" | "unavailable";

export interface ServiceHealth {
  service: string;
  status: ServiceStatus;
  latency_ms: number;
  checked_at: string;
  message: string;
}

export interface SystemHealth {
  status: "healthy" | "degraded";
  services: {
    postgres: ServiceHealth;
    mongodb: ServiceHealth;
  };
}

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function fetchSystemHealth(): Promise<SystemHealth> {
  const response = await fetch(`${API_URL}/api/health`);
  if (!response.ok) throw new Error("상태 정보를 불러오지 못했습니다.");
  return response.json() as Promise<SystemHealth>;
}