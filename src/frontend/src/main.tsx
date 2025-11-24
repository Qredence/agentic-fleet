// Must be imported first to ensure Tailwind layers and style foundations are defined before any component styles
import "./index.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { AppsSDKUIProvider } from "@openai/apps-sdk-ui/components/AppsSDKUIProvider";
import App from "./App.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AppsSDKUIProvider
      linkComponent={"a" as unknown as React.ComponentType<unknown>}
    >
      <App />
    </AppsSDKUIProvider>
  </StrictMode>,
);
