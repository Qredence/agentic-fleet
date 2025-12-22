import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./root/App";
import { ThemeProvider } from "@/contexts";
import { QueryProvider } from "@/api";
import { TooltipProvider } from "@/components/ui/tooltip";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryProvider>
      <ThemeProvider defaultTheme="dark">
        <TooltipProvider>
          <App />
        </TooltipProvider>
      </ThemeProvider>
    </QueryProvider>
  </StrictMode>,
);
