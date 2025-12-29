import {
  Sidebar,
  SidebarContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarTrigger,
} from "@/components/ui";

export const SidebarRight = ({
  ...props
}: React.ComponentProps<typeof Sidebar>) => {
  return (
    <Sidebar collapsible="offcanvas" side="right" variant="floating" {...props}>
      <SidebarHeader className="flex flex-row items-center justify-between px-4 py-4">
        <SidebarGroupLabel>Details</SidebarGroupLabel>
        <SidebarTrigger className="size-8" />
      </SidebarHeader>
      <SidebarContent className="px-4">
        <div className="text-sm text-muted-foreground">
          Select an item to view details.
        </div>
      </SidebarContent>
    </Sidebar>
  );
};
