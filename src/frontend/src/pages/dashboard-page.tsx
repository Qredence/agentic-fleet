import { OptimizationDashboard } from "@/components/dashboard";
import { SidebarLeft } from "@/components/layout";
import { SidebarInset } from "@/components/ui";

/**
 * DashboardPage - Optimization dashboard view
 * Sidebar is provided by App.tsx SidebarProvider
 */
export function DashboardPage() {
  return (
    <>
      <SidebarLeft />
      <SidebarInset className="flex flex-col h-screen overflow-hidden transition-all duration-200">
        <OptimizationDashboard />
      </SidebarInset>
    </>
  );
}
