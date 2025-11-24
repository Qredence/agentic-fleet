/**
 * Shared test utilities
 */

const encoder = new TextEncoder();

/**
 * Creates a ReadableStream from an array of string chunks
 * Useful for testing SSE stream parsing
 */
export function makeStream(chunks: string[]): ReadableStream<Uint8Array> {
  return new ReadableStream({
    start(controller) {
      chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)));
      controller.close();
    },
  });
}
