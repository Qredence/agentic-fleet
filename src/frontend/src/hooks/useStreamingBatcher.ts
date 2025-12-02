import { useRef, useCallback, useEffect } from "react";

interface UseStreamingBatcherOptions<T> {
  /** Callback when batch is ready to be applied */
  onBatch: (accumulatedValue: T) => void;
  /** Initial value for accumulation */
  initialValue: T;
  /** How to merge new value with accumulated value */
  merge: (accumulated: T, incoming: T) => T;
  /** Minimum time between batches in ms (default: 16ms = 60fps) */
  minBatchInterval?: number;
  /** Maximum time to wait before forcing a batch (default: 100ms) */
  maxBatchDelay?: number;
}

/**
 * Hook that batches rapid updates using requestAnimationFrame.
 * Prevents UI thrashing during high-frequency streaming events.
 *
 * @example
 * ```tsx
 * const { push, flush } = useStreamingBatcher({
 *   onBatch: (text) => setContent(prev => prev + text),
 *   initialValue: "",
 *   merge: (acc, incoming) => acc + incoming,
 * });
 *
 * // In SSE handler:
 * push(delta);
 * ```
 */
export function useStreamingBatcher<T>({
  onBatch,
  initialValue,
  merge,
  minBatchInterval = 16,
  maxBatchDelay = 100,
}: UseStreamingBatcherOptions<T>) {
  const accumulatedRef = useRef<T>(initialValue);
  const rafIdRef = useRef<number | null>(null);
  const lastBatchTimeRef = useRef<number>(0);
  const maxDelayTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hasPendingRef = useRef<boolean>(false);

  const executeBatch = useCallback(() => {
    if (!hasPendingRef.current) return;

    const now = performance.now();
    const timeSinceLastBatch = now - lastBatchTimeRef.current;

    if (timeSinceLastBatch >= minBatchInterval) {
      onBatch(accumulatedRef.current);
      accumulatedRef.current = initialValue;
      lastBatchTimeRef.current = now;
      hasPendingRef.current = false;

      // Clear any pending max delay timeout
      if (maxDelayTimeoutRef.current) {
        clearTimeout(maxDelayTimeoutRef.current);
        maxDelayTimeoutRef.current = null;
      }
    } else {
      // Schedule next attempt
      rafIdRef.current = requestAnimationFrame(executeBatch);
    }
  }, [onBatch, initialValue, minBatchInterval]);

  const push = useCallback(
    (value: T) => {
      accumulatedRef.current = merge(accumulatedRef.current, value);
      hasPendingRef.current = true;

      // Schedule batch if not already scheduled
      if (rafIdRef.current === null) {
        rafIdRef.current = requestAnimationFrame(executeBatch);
      }

      // Set up max delay timeout if not already set
      if (maxDelayTimeoutRef.current === null) {
        maxDelayTimeoutRef.current = setTimeout(() => {
          if (hasPendingRef.current) {
            onBatch(accumulatedRef.current);
            accumulatedRef.current = initialValue;
            hasPendingRef.current = false;
            lastBatchTimeRef.current = performance.now();
          }
          maxDelayTimeoutRef.current = null;
        }, maxBatchDelay);
      }
    },
    [merge, executeBatch, onBatch, initialValue, maxBatchDelay],
  );

  const flush = useCallback(() => {
    if (rafIdRef.current !== null) {
      cancelAnimationFrame(rafIdRef.current);
      rafIdRef.current = null;
    }
    if (maxDelayTimeoutRef.current !== null) {
      clearTimeout(maxDelayTimeoutRef.current);
      maxDelayTimeoutRef.current = null;
    }
    if (hasPendingRef.current) {
      onBatch(accumulatedRef.current);
      accumulatedRef.current = initialValue;
      hasPendingRef.current = false;
      lastBatchTimeRef.current = performance.now();
    }
  }, [onBatch, initialValue]);

  const reset = useCallback(() => {
    if (rafIdRef.current !== null) {
      cancelAnimationFrame(rafIdRef.current);
      rafIdRef.current = null;
    }
    if (maxDelayTimeoutRef.current !== null) {
      clearTimeout(maxDelayTimeoutRef.current);
      maxDelayTimeoutRef.current = null;
    }
    accumulatedRef.current = initialValue;
    hasPendingRef.current = false;
  }, [initialValue]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (rafIdRef.current !== null) {
        cancelAnimationFrame(rafIdRef.current);
      }
      if (maxDelayTimeoutRef.current !== null) {
        clearTimeout(maxDelayTimeoutRef.current);
      }
    };
  }, []);

  return { push, flush, reset };
}

/**
 * Specialized batcher for string concatenation (common in streaming text).
 */
export function useTextStreamingBatcher(
  onBatch: (text: string) => void,
  options?: Partial<
    Omit<
      UseStreamingBatcherOptions<string>,
      "onBatch" | "initialValue" | "merge"
    >
  >,
) {
  return useStreamingBatcher<string>({
    onBatch,
    initialValue: "",
    merge: (acc, incoming) => acc + incoming,
    ...options,
  });
}

/**
 * Specialized batcher for array accumulation (events, steps, etc.).
 */
export function useArrayStreamingBatcher<T>(
  onBatch: (items: T[]) => void,
  options?: Partial<
    Omit<UseStreamingBatcherOptions<T[]>, "onBatch" | "initialValue" | "merge">
  >,
) {
  return useStreamingBatcher<T[]>({
    onBatch,
    initialValue: [],
    merge: (acc, incoming) => [...acc, ...incoming],
    ...options,
  });
}
