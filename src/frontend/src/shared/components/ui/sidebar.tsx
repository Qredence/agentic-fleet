import { cn } from "@/shared/lib/utils";
import { useIsMobile } from "@/shared/hooks/useMobile";
import { Button } from "./button";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "./sheet";
import { Slot } from "@radix-ui/react-slot";
import { PanelLeft } from "lucide-react";
import * as React from "react";

type SidebarContextValue = {
  isMobile: boolean;
  open: boolean;
  setOpen: (open: boolean) => void;
  openMobile: boolean;
  setOpenMobile: (open: boolean) => void;
  toggleSidebar: () => void;
};

const SidebarContext = React.createContext<SidebarContextValue | null>(null);

function useSidebar() {
  const context = React.useContext(SidebarContext);
  if (!context) {
    throw new Error("useSidebar must be used within a SidebarProvider.");
  }
  return context;
}

export function SidebarProvider({
  defaultOpen = true,
  className,
  children,
  ...props
}: React.ComponentProps<"div"> & { defaultOpen?: boolean }) {
  const isMobile = useIsMobile();
  const [open, setOpen] = React.useState(defaultOpen);
  const [openMobile, setOpenMobile] = React.useState(false);

  const toggleSidebar = React.useCallback(() => {
    if (isMobile) {
      setOpenMobile((prev) => !prev);
      return;
    }
    setOpen((prev) => !prev);
  }, [isMobile]);

  const value = React.useMemo<SidebarContextValue>(
    () => ({
      isMobile,
      open,
      setOpen,
      openMobile,
      setOpenMobile,
      toggleSidebar,
    }),
    [isMobile, open, openMobile, toggleSidebar],
  );

  return (
    <SidebarContext.Provider value={value}>
      <div className={cn("flex min-h-svh w-full", className)} {...props}>
        {children}
      </div>
    </SidebarContext.Provider>
  );
}

export function Sidebar({
  side = "left",
  className,
  children,
  ...props
}: React.ComponentProps<"aside"> & { side?: "left" | "right" }) {
  const { isMobile, open, openMobile, setOpenMobile } = useSidebar();

  if (isMobile) {
    return (
      <Sheet open={openMobile} onOpenChange={setOpenMobile}>
        <SheetContent
          side={side}
          className={cn(
            "w-72 p-0 bg-background text-foreground border-border",
            className,
          )}
        >
          <SheetHeader className="sr-only">
            <SheetTitle>Sidebar</SheetTitle>
          </SheetHeader>
          <aside className="flex h-full w-full flex-col" {...props}>
            {children}
          </aside>
        </SheetContent>
      </Sheet>
    );
  }

  return (
    <aside
      className={cn(
        "hidden md:flex h-svh flex-col border-r border-border bg-background text-foreground transition-[width] duration-200 ease-linear",
        open ? "w-64" : "w-14",
        className,
      )}
      {...props}
    >
      {children}
    </aside>
  );
}

export function SidebarInset({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div className={cn("flex min-w-0 flex-1 flex-col", className)} {...props} />
  );
}

export function SidebarTrigger({
  className,
  onClick,
  ...props
}: React.ComponentProps<typeof Button>) {
  const { toggleSidebar } = useSidebar();

  return (
    <Button
      variant="ghost"
      size="icon"
      className={cn("h-8 w-8", className)}
      onClick={(event) => {
        onClick?.(event);
        toggleSidebar();
      }}
      aria-label="Toggle sidebar"
      {...props}
    >
      <PanelLeft className="h-4 w-4" />
    </Button>
  );
}

export function SidebarHeader({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return <div className={cn("border-b border-border", className)} {...props} />;
}

export function SidebarContent({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return <div className={cn("flex-1 overflow-y-auto", className)} {...props} />;
}

export function SidebarGroup({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return <div className={cn("px-2 py-1", className)} {...props} />;
}

export function SidebarGroupLabel({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      className={cn(
        "px-2 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wide",
        className,
      )}
      {...props}
    />
  );
}

export function SidebarMenu({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return <div className={cn("space-y-1", className)} {...props} />;
}

export function SidebarMenuButton({
  asChild = false,
  isActive = false,
  className,
  ...props
}: React.ComponentProps<"button"> & { asChild?: boolean; isActive?: boolean }) {
  const Comp = asChild ? Slot : "button";

  return (
    <Comp
      data-active={isActive}
      className={cn(
        "flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30",
        isActive && "bg-muted text-foreground font-medium",
        className,
      )}
      {...props}
    />
  );
}
