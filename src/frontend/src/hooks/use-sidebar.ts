import * as React from "react";

const SIDEBAR_COOKIE_NAME = "sidebar_state";

export type SidebarContextProps = {
  state: "expanded" | "collapsed";
  open: boolean;
  setOpen: (open: boolean) => void;
  openMobile: boolean;
  setOpenMobile: (open: boolean) => void;
  isMobile: boolean;
  toggleSidebar: () => void;
};

export const SidebarContext = React.createContext<SidebarContextProps | null>(
  null,
);

/**
 * Reads the sidebar state from cookies
 */
function getInitialOpenState(defaultOpen: boolean): boolean {
  if (typeof document === "undefined") {
    return defaultOpen;
  }

  const cookie = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${SIDEBAR_COOKIE_NAME}=`));

  if (!cookie) {
    return defaultOpen;
  }

  const value = cookie.split("=")[1];
  return value === "true";
}

export function useSidebar() {
  const context = React.useContext(SidebarContext);
  if (!context) {
    throw new Error("useSidebar must be used within a SidebarProvider.");
  }

  return context;
}

export { getInitialOpenState, SIDEBAR_COOKIE_NAME };
