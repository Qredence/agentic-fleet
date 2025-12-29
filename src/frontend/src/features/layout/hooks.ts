import * as React from "react";

// =============================================================================
// Constants
// =============================================================================

const SIDEBAR_COOKIE_NAME = "sidebar:state";
const SIDEBAR_COOKIE_MAX_AGE = 60 * 60 * 24 * 7;

// =============================================================================
// Types
// =============================================================================

interface SidebarContextProps {
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
  openMobile: boolean;
  setOpenMobile: React.Dispatch<React.SetStateAction<boolean>>;
  isMobile: boolean;
  toggleSidebar: () => void;
  state?: "expanded" | "collapsed";
}

const SidebarContext = React.createContext<SidebarContextProps | null>(null);

// =============================================================================
// Helpers
// =============================================================================

function getInitialOpenState(defaultOpen = true): boolean {
  // Check localStorage for sidebar state
  if (typeof window !== "undefined") {
    try {
      const stored = localStorage.getItem(SIDEBAR_COOKIE_NAME);
      if (stored !== null) return stored === "true";
    } catch {
      // Fall through to default
    }
  }
  return defaultOpen;
}

// =============================================================================
// Hooks
// =============================================================================

export function useSidebar() {
  const context = React.useContext(SidebarContext);
  if (!context) {
    throw new Error("useSidebar must be used within a SidebarProvider");
  }
  return context;
}

export {
  SidebarContext,
  getInitialOpenState,
  SIDEBAR_COOKIE_NAME,
  SIDEBAR_COOKIE_MAX_AGE,
};
export type { SidebarContextProps };
