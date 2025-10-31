import React from "react";
import { createRoot } from "react-dom/client";
import ChatPage from "./features/chat/ChatPage";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ChatPage />
  </React.StrictMode>,
);
