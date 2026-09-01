import { apiGet } from "./client";

export type ServiceStatus = "healthy" | "unavailable";

export interface ServiceHealth {
  service: string;
  status: ServiceStatus;
  latency_ms: number;
  checked_at: string;
  message: string;
  version: string | null;
}

export interface SystemHealth {
  status: "healthy" | "degraded";
  services: {
    postgres: ServiceHealth;
    mongodb: ServiceHealth;
  };
}

export async function fetchSystemHealth(): Promise<SystemHealth> {
  return apiGet<SystemHealth>("/api/health");
}
