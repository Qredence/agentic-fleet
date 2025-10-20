import type {
  ApprovalActionState,
  ChatStatus,
  Message,
  PendingApproval,
} from "@/lib/use-fastapi-chat";
import { create } from "zustand";
import { immer } from "zustand/middleware/immer";

interface ChatState {
  messages: Message[];
  input: string;
  status: ChatStatus;
  error: Error | null;
  conversationId?: string;
  pendingApprovals: PendingApproval[];
  approvalStatuses: Record<string, ApprovalActionState>;
  messageToolCalls: Record<string, any[]>;
}

interface ChatActions {
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  updateMessage: (id: string, content: string, toolCalls?: any[]) => void;
  setInput: (input: string) => void;
  setStatus: (status: ChatStatus) => void;
  setError: (error: Error | null) => void;
  setConversationId: (conversationId?: string) => void;
  addPendingApproval: (approval: PendingApproval) => void;
  removePendingApproval: (requestId: string) => void;
  setApprovalStatus: (requestId: string, status: ApprovalActionState) => void;
  addToolCall: (messageId: string, toolCall: any) => void;
  updateToolCall: (
    messageId: string,
    toolCallId: string,
    output: any,
    errorText?: string
  ) => void;
  clearMessages: () => void;
}

const initialState: ChatState = {
  messages: [],
  input: "",
  status: "ready",
  error: null,
  conversationId: undefined,
  pendingApprovals: [],
  approvalStatuses: {},
  messageToolCalls: {},
};

export const useChatStore = create<ChatState & ChatActions>()(
  immer((set) => ({
    ...initialState,
    setMessages: (messages) => set({ messages }),
    addMessage: (message) =>
      set((state) => {
        state.messages.push(message);
      }),
    updateMessage: (id, content, toolCalls) =>
      set((state) => {
        const message = state.messages.find((m) => m.id === id);
        if (message) {
          message.content = content;
          if (toolCalls) {
            message.toolCalls = toolCalls;
          }
        }
      }),
    setInput: (input) => set({ input }),
    setStatus: (status) => set({ status }),
    setError: (error) => set({ error }),
    setConversationId: (conversationId) => set({ conversationId }),
    addPendingApproval: (approval) =>
      set((state) => {
        if (
          !state.pendingApprovals.some(
            (a) => a.requestId === approval.requestId
          )
        ) {
          state.pendingApprovals.push(approval);
          state.approvalStatuses[approval.requestId] = { status: "idle" };
        }
      }),
    removePendingApproval: (requestId) =>
      set((state) => {
        state.pendingApprovals = state.pendingApprovals.filter(
          (a) => a.requestId !== requestId
        );
        delete state.approvalStatuses[requestId];
      }),
    setApprovalStatus: (requestId, status) =>
      set((state) => {
        state.approvalStatuses[requestId] = status;
      }),
    addToolCall: (messageId, toolCall) =>
      set((state) => {
        if (!state.messageToolCalls[messageId]) {
          state.messageToolCalls[messageId] = [];
        }
        state.messageToolCalls[messageId].push(toolCall);
      }),
    updateToolCall: (messageId, toolCallId, output, errorText) =>
      set((state) => {
        const toolCalls = state.messageToolCalls[messageId];
        if (toolCalls) {
          const toolCall = toolCalls.find((tc) => tc.id === toolCallId);
          if (toolCall) {
            toolCall.output = output;
            toolCall.errorText = errorText;
            toolCall.state = errorText ? "output-error" : "output-available";
          }
        }
      }),
    clearMessages: () => set(initialState),
  }))
);
