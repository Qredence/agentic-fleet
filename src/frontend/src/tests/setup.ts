import "@testing-library/jest-dom/vitest";
import React from "react";
import { afterAll, beforeAll, vi } from "vitest";
import type { ReactNode } from "react";

// Types for Virtuoso mock
interface VirtuosoMockProps {
  data?: unknown[];
  itemContent: (index: number, data: unknown) => ReactNode;
  className?: string;
}

// Mock react-virtuoso to render items synchronously in tests so queries can find content
// The real Virtuoso relies on browser measurement APIs which are flaky in jsdom.
vi.mock("react-virtuoso", () => {
  const Virtuoso = ({ data, itemContent, className }: VirtuosoMockProps) => {
    return (
      // Render a simple container with items expanded so tests can query text
      React.createElement(
        "div",
        { className },
        data?.map((d: unknown, i: number) =>
          React.createElement(
            "div",
            { key: i, "data-testid": `virtuoso-item-${i}` },
            itemContent(i, d),
          ),
        ),
      )
    );
  };

  return { Virtuoso };
});

// Polyfill for browser APIs that don't exist in jsdom but don't need mocking

// localStorage/sessionStorage mock for jsdom
// Many components (chatStore, ThemeContext) depend on storage APIs
const createStorageMock = () => {
  const store = new Map<string, string>();
  return {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => store.set(key, value),
    removeItem: (key: string) => store.delete(key),
    clear: () => store.clear(),
    get length() {
      return store.size;
    },
    key: (index: number) => {
      const keys = Array.from(store.keys());
      return keys[index] ?? null;
    },
  };
};

Object.defineProperty(window, "localStorage", {
  value: createStorageMock(),
  writable: true,
});

Object.defineProperty(window, "sessionStorage", {
  value: createStorageMock(),
  writable: true,
});

// ResizeObserver polyfill for DOM tests
globalThis.ResizeObserver =
  globalThis.ResizeObserver ||
  class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };

// IntersectionObserver polyfill for DOM tests
globalThis.IntersectionObserver =
  globalThis.IntersectionObserver ||
  class IntersectionObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };

// matchMedia polyfill for DOM tests
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => true,
  }),
});

// scrollTo polyfill for jsdom (used by motion during keyframe measurement)
// jsdom defines scrollTo but throws "Not implemented", so we override.
Object.defineProperty(window, "scrollTo", { value: () => {}, writable: true });

beforeAll(() => {
  console.log("🧪 Setting up frontend test environment with fetch mocks");

  // Mock fetch globally for all tests
  const mockFetch = vi.fn();
  vi.stubGlobal("fetch", mockFetch);

  mockFetch.mockImplementation(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();

      console.log(`🔍 Mock fetch called with: ${url}`);

      // Mock health endpoint
      if (url.includes("/api/health") || url.endsWith("/health")) {
        console.log("✅ Mocking health endpoint");
        return new Response(JSON.stringify({ status: "ok" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }

      // Mock create conversation (both /v1 and direct)
      if (url.includes("/conversations") && init?.method === "POST") {
        console.log("✅ Mocking create conversation");
        return new Response(
          JSON.stringify({
            id: "conv-mock-123",
            title: "Mock Conversation",
            created_at: Date.now(),
            messages: [],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }

      // Mock get conversation
      if (url.match(/\/api\/conversations\/[^/]+$/)) {
        console.log("✅ Mocking get conversation");
        return new Response(
          JSON.stringify({
            id: "conv-mock-123",
            title: "Mock Conversation",
            created_at: Date.now(),
            messages: [],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }

      // Mock send chat
      if (url.includes("/api/chat") && init?.method === "POST") {
        console.log("✅ Mocking send chat");
        const body = init?.body ? JSON.parse(init.body as string) : {};
        const userMessage = body.message || "(no message)";
        return new Response(
          JSON.stringify({
            conversation_id: body.conversation_id || "conv-mock-123",
            message: userMessage,
            messages: [
              {
                id: `user-${Date.now()}`,
                role: "user",
                content: userMessage,
                created_at: Date.now(),
              },
              {
                id: `assistant-${Date.now()}`,
                role: "assistant",
                content: `Echo: ${userMessage}`,
                created_at: Date.now(),
              },
            ],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }

      // Default fallback - should not happen in our tests
      console.warn(`⚠️ Unmocked fetch call: ${url}`);
      return new Response(JSON.stringify({ error: "Not mocked" }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      });
    },
  );
});

afterAll(() => {
  vi.restoreAllMocks();
  console.log("✅ Frontend tests completed");
});
