import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { ToastComponent } from "./toast";
import { cn } from "@/lib/utils";

export type ToastVariant =
  | "default"
  | "destructive"
  | "success"
  | "warning"
  | "info";

export interface ToastData {
  id: string;
  title?: string;
  description?: string;
  variant?: ToastVariant;
  duration?: number;
  action?: React.ReactNode;
}

interface ToasterProps {
  toasts: ToastData[];
  onRemove: (id: string) => void;
}

export function Toaster({ toasts, onRemove }: ToasterProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return createPortal(
    <div
      className={cn(
        "fixed top-0 z-100 flex max-h-screen w-full flex-col-reverse p-4 sm:bottom-0 sm:right-0 sm:top-auto sm:flex-col md:max-w-[420px]",
      )}
    >
      {toasts.map((toast) => (
        <ToastComponent
          key={toast.id}
          title={toast.title}
          description={toast.description}
          variant={toast.variant}
          action={toast.action}
          onClose={() => onRemove(toast.id)}
          className="mb-2"
        />
      ))}
    </div>,
    document.body,
  );
}
