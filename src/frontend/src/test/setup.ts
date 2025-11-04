import "@testing-library/jest-dom";
import { afterAll, beforeAll } from "vitest";

// Polyfill for browser APIs that don't exist in jsdom but don't need mocking

// ResizeObserver polyfill for DOM tests
global.ResizeObserver =
  global.ResizeObserver ||
  class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };

// IntersectionObserver polyfill for DOM tests
global.IntersectionObserver =
  global.IntersectionObserver ||
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

beforeAll(() => {
  // Global test setup - using real API connections
  console.log("🧪 Setting up frontend test environment with real API");
  console.log(
    "📡 Backend API URL:",
    import.meta.env.VITE_API_URL || "http://localhost:8000",
  );
});

afterAll(() => {
  console.log("✅ Frontend tests completed");
});
