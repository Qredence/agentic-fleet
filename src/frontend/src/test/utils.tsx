import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderOptions } from "@testing-library/react";
import React from "react";

/**
 * Custom render function that includes providers
 */
export function renderWithProviders(
  ui: React.ReactElement,
  options?: Omit<RenderOptions, "wrapper">,
) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }

  return render(ui, { wrapper: Wrapper, ...options });
}

/**
 * Mock fetch responses
 */
export function mockFetchResponse(
  data: unknown,
  init?: ResponseInit,
): Response {
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { "Content-Type": "application/json" },
    ...init,
  });
}

/**
 * Mock fetch error
 */
export function mockFetchError(message: string, status = 500): Response {
  return new Response(JSON.stringify({ error: message }), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

// Re-export everything from testing library
export * from "@testing-library/react";
export { default as userEvent } from "@testing-library/user-event";
