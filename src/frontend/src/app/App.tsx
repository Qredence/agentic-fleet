import { useEffect, useState, lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { ErrorBoundary } from "@/components/error-boundary";
import { SidebarProvider } from "@/components/ui/sidebar";
import { useToast, setGlobalToastInstance } from "@/hooks/use-toast";
import { Toaster } from "@/components/ui/toaster";
import { Loader2 } from "lucide-react";

// Lazy load route components
const ChatPage = lazy(() =>
  import("@/features/chat").then((module) => ({ default: module.ChatPage })),
);
const DashboardPage = lazy(() =>
  import("@/features/dashboard").then((module) => ({
    default: module.DashboardPage,
  })),
);

function LoadingSpinner() {
  return (
    <div className="flex h-screen w-full items-center justify-center bg-background">
      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
    </div>
  );
}

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
        <Suspense fallback={<LoadingSpinner />}>
          <Routes>
            <Route path="/" element={<ChatPage />} />
            <Route path="/chat/:id" element={<ChatPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
        <Toaster toasts={toast.toasts} onRemove={toast.dismiss} />
      </SidebarProvider>
    </ErrorBoundary>
  );
}

export default App;
