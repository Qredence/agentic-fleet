import type { ReactNode } from "react";
import { QueryProvider } from "@/api";
import { ThemeProvider } from "@/contexts";
import { TooltipProvider } from "@/components/ui/tooltip";

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <QueryProvider>
      <ThemeProvider defaultTheme="dark">
        <TooltipProvider>{children}</TooltipProvider>
      </ThemeProvider>
    </QueryProvider>
  );
}
