/**
 * Query Client Provider
 *
 * React Query client configuration and provider setup.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

interface QueryProviderProps {
  children: ReactNode;
}

/**
 * QueryProvider wrapper component.
 * Creates a stable QueryClient instance.
 */
export function QueryProvider({ children }: QueryProviderProps) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // Don't refetch on window focus by default
            refetchOnWindowFocus: false,
            // Retry failed requests once
            retry: 1,
            // Consider data stale after 30 seconds
            staleTime: 30_000,
            // Keep unused data in cache for 5 minutes
            gcTime: 5 * 60_000,
          },
          mutations: {
            // Don't retry mutations by default
            retry: false,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
