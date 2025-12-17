/**
 * HTTP Client
 *
 * A typed fetch wrapper with retry logic, error handling, and AbortController support.
 */

import {
  API_PREFIX,
  API_TIMEOUT,
  MAX_RETRIES,
  RETRY_BASE_DELAY,
} from "./config";
import { ApiRequestError, type ApiError } from "./types";

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  timeout?: number;
  retries?: number;
  signal?: AbortSignal;
}

/**
 * Parse error response from the API.
 */
async function parseErrorResponse(response: Response): Promise<ApiError> {
  try {
    const data = await response.json();
    return {
      message: data.detail || data.message || response.statusText,
      status: response.status,
      code: data.code,
      details: data,
    };
  } catch {
    return {
      message: response.statusText || "Unknown error",
      status: response.status,
    };
  }
}

/**
 * Sleep for a given number of milliseconds.
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Calculate exponential backoff delay.
 */
function getBackoffDelay(
  attempt: number,
  baseDelay: number = RETRY_BASE_DELAY,
): number {
  return Math.min(baseDelay * Math.pow(2, attempt), 10000);
}

/**
 * Check if an error is retryable.
 */
function isRetryableError(status: number): boolean {
  // Retry on network errors (status 0), server errors (5xx), and rate limiting (429)
  return status === 0 || status === 429 || (status >= 500 && status < 600);
}

/**
 * Make an HTTP request with retry logic and error handling.
 */
export async function request<T>(
  endpoint: string,
  options: RequestOptions = {},
): Promise<T> {
  const {
    body,
    timeout = API_TIMEOUT,
    retries = MAX_RETRIES,
    signal: externalSignal,
    ...fetchOptions
  } = options;

  const url = endpoint.startsWith("http")
    ? endpoint
    : `${API_PREFIX}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;

  // Create a timeout controller that can be combined with external signal
  const timeoutController = new AbortController();
  const timeoutId = setTimeout(() => timeoutController.abort(), timeout);

  // Combine signals if an external one is provided
  const signal = externalSignal
    ? anySignal([externalSignal, timeoutController.signal])
    : timeoutController.signal;

  let lastError: ApiError | null = null;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const response = await fetch(url, {
        ...fetchOptions,
        body: body ? JSON.stringify(body) : undefined,
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          ...fetchOptions.headers,
        },
        signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const error = await parseErrorResponse(response);

        // If it's a retryable error and we have retries left, continue
        if (isRetryableError(response.status) && attempt < retries) {
          lastError = error;
          const delay = getBackoffDelay(attempt);
          console.warn(
            `Request failed (attempt ${attempt + 1}/${retries + 1}), retrying in ${delay}ms:`,
            error.message,
          );
          await sleep(delay);
          continue;
        }

        throw new ApiRequestError(error);
      }

      // Handle empty responses (204 No Content)
      if (response.status === 204) {
        return undefined as T;
      }

      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);

      // Don't retry if aborted
      if (error instanceof Error && error.name === "AbortError") {
        throw new ApiRequestError({
          message: "Request was cancelled",
          status: 0,
          code: "ABORTED",
        });
      }

      // Network error - retry if attempts remaining
      if (error instanceof TypeError && attempt < retries) {
        lastError = {
          message: "Network error",
          status: 0,
          code: "NETWORK_ERROR",
        };
        const delay = getBackoffDelay(attempt);
        console.warn(
          `Network error (attempt ${attempt + 1}/${retries + 1}), retrying in ${delay}ms`,
        );
        await sleep(delay);
        continue;
      }

      // Re-throw ApiRequestError as-is
      if (error instanceof ApiRequestError) {
        throw error;
      }

      // Wrap other errors
      throw new ApiRequestError({
        message: error instanceof Error ? error.message : "Unknown error",
        status: 0,
        code: "UNKNOWN_ERROR",
      });
    }
  }

  // If we exhausted all retries, throw the last error
  throw new ApiRequestError(
    lastError || { message: "Request failed", status: 0 },
  );
}

/**
 * Combine multiple AbortSignals into one.
 * The combined signal aborts when any of the input signals abort.
 */
function anySignal(signals: AbortSignal[]): AbortSignal {
  const controller = new AbortController();

  for (const signal of signals) {
    if (signal.aborted) {
      controller.abort(signal.reason);
      return controller.signal;
    }

    signal.addEventListener("abort", () => controller.abort(signal.reason), {
      once: true,
    });
  }

  return controller.signal;
}

// Convenience methods
export const http = {
  get: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: "GET" }),

  post: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: "POST", body }),

  put: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: "PUT", body }),

  delete: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: "DELETE" }),

  patch: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    request<T>(endpoint, { ...options, method: "PATCH", body }),
};

export default http;
