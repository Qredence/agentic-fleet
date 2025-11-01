import { create } from "zustand";

interface ConversationStore {
  activeConversationId: string | undefined;
  setActiveConversationId: (id: string | undefined) => void;
}

export const useConversationStore = create<ConversationStore>((set) => ({
  activeConversationId: undefined,
  setActiveConversationId: (id) => set({ activeConversationId: id }),
}));
