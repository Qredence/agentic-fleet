import { useQuery } from "@tanstack/react-query";
import { buildApiUrl } from "../api-config";

export interface Entity {
  id: string;
  name?: string;
  type?: string;
  description?: string;
}

/**
 * Query hook for fetching entity list
 */
export function useEntities() {
  return useQuery<Entity[]>({
    queryKey: ["entities"],
    queryFn: async () => {
      const response = await fetch(buildApiUrl("/v1/entities"));
      if (!response.ok) {
        throw new Error(`Failed to fetch entities: ${response.status}`);
      }
      const data = await response.json();
      return Array.isArray(data?.data) ? data.data : [];
    },
    staleTime: 10 * 60 * 1000, // 10 minutes - entities don't change often
  });
}

/**
 * Query hook for fetching single entity info
 */
export function useEntityInfo(entityId: string | undefined) {
  return useQuery({
    queryKey: ["entities", entityId],
    queryFn: async () => {
      if (!entityId) {
        return null;
      }
      const response = await fetch(
        buildApiUrl(`/v1/entities/${entityId}/info`),
      );
      if (!response.ok) {
        throw new Error(`Failed to fetch entity info: ${response.status}`);
      }
      return response.json() as Promise<Entity>;
    },
    enabled: !!entityId,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}
