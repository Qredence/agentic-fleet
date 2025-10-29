import { apiRequest } from "./client";
import type { ChatExecutionRequest, ChatExecutionResponse } from "../types";

export const createChatExecution = (payload: ChatExecutionRequest) =>
  apiRequest<ChatExecutionResponse>("/v1/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
