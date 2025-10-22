import { http, HttpResponse } from "msw";

export const handlers = [
  http.post("http://localhost:8000/v1/conversations", () => {
    return HttpResponse.json({ id: "test-conv-id" });
  }),
  http.post("http://localhost:8000/v1/responses", () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(
          encoder.encode('data: {"type":"response.output_text.delta","delta":"Hello"}\n\n')
        );
        controller.enqueue(
          encoder.encode('data: {"type":"response.output_text.delta","delta":", "}\n\n')
        );
        controller.enqueue(
          encoder.encode('data: {"type":"response.output_text.delta","delta":"world!"}\n\n')
        );
        controller.enqueue(encoder.encode("data: [DONE]\n\n"));
        controller.close();
      },
    });
    return new HttpResponse(stream, {
      headers: {
        "Content-Type": "text/event-stream",
      },
    });
  }),
];
