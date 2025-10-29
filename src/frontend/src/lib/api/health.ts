import { apiRequest } from "./client";
import type { HealthResponse } from "../types";

export const checkHealth = () => apiRequest<HealthResponse>("/health");
