import { useCallback, useRef, useState } from "react";
import type { ToastData } from "@/components/ui/toaster";

let toastIdCounter = 0;

function generateToastId(): string {
  return `toast-${Date.now()}-${++toastIdCounter}`;
}

interface UseToastReturn {
  toasts: ToastData[];
  toast: (data: Omit<ToastData, "id">) => string;
  dismiss: (id: string) => void;
  dismissAll: () => void;
}

export function useToast(): UseToastReturn {
  const [toasts, setToasts] = useState<ToastData[]>([]);
  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(
    new Map(),
  );

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
    const timer = timersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }
  }, []);

  const dismissAll = useCallback(() => {
    timersRef.current.forEach((timer) => clearTimeout(timer));
    timersRef.current.clear();
    setToasts([]);
  }, []);

  const toast = useCallback(
    (data: Omit<ToastData, "id">): string => {
      const id = generateToastId();
      const duration = data.duration ?? 5000;

      const newToast: ToastData = {
        ...data,
        id,
        variant: data.variant ?? "default",
      };

      setToasts((prev) => [...prev, newToast]);

      // Auto-dismiss after duration
      if (duration > 0) {
        const timer = setTimeout(() => {
          dismiss(id);
        }, duration);
        timersRef.current.set(id, timer);
      }

      return id;
    },
    [dismiss],
  );

  return {
    toasts,
    toast,
    dismiss,
    dismissAll,
  };
}

// Global toast instance for use outside React components
let globalToastInstance: UseToastReturn | null = null;

export function setGlobalToastInstance(instance: UseToastReturn): void {
  globalToastInstance = instance;
}

export function getGlobalToastInstance(): UseToastReturn | null {
  return globalToastInstance;
}

// Convenience functions for common toast types
export function createToastHelpers(
  toastFn: (data: Omit<ToastData, "id">) => string,
) {
  return {
    success: (title: string, description?: string) =>
      toastFn({ title, description, variant: "success" }),
    error: (title: string, description?: string) =>
      toastFn({ title, description, variant: "destructive" }),
    warning: (title: string, description?: string) =>
      toastFn({ title, description, variant: "warning" }),
    info: (title: string, description?: string) =>
      toastFn({ title, description, variant: "info" }),
  };
}
