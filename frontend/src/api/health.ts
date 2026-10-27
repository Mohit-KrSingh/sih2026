import { api } from "./client";

export interface HealthResponse {
  status: string;
  timestamp: string;
  version: string;
  services: {
    database: string;
    redis: string;
  };
  demo_mode: boolean;
}

export async function getHealthApi(): Promise<HealthResponse> {
  return api.get<HealthResponse>("/api/v1/health");
}
