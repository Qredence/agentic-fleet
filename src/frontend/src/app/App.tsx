import { useEffect, useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { ChatPage } from "@/features/chat";
import { DashboardPage } from "@/features/dashboard";
import { ErrorBoundary } from "@/components/error-boundary";
import { SidebarProvider } from "@/components/ui/sidebar";
import { useToast, setGlobalToastInstance } from "@/hooks/use-toast";
import { Toaster } from "@/components/ui/toaster";

function App() {
  const toast = useToast();

  // Set global toast instance for use outside React components
  useEffect(() => {
    setGlobalToastInstance(toast);
  }, [toast]);

  // Keep sidebar always open/visible
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <ErrorBoundary>
      <SidebarProvider open={sidebarOpen} onOpenChange={setSidebarOpen}>
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/chat/:id" element={<ChatPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <Toaster toasts={toast.toasts} onRemove={toast.dismiss} />
      </SidebarProvider>
    </ErrorBoundary>
  );
}

export default App;
