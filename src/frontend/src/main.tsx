import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./app/index.css";
import App from "./app/App";
import { ThemeProvider } from "@/shared/contexts";
import { QueryProvider } from "@/api";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryProvider>
      <ThemeProvider defaultTheme="dark">
        <App />
      </ThemeProvider>
    </QueryProvider>
  </StrictMode>,
);
