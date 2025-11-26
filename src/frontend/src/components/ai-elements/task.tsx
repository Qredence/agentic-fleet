import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ChevronDown,
  CheckCircle2,
  XCircle,
  Loader2,
  Circle,
} from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface TaskProps {
  children: React.ReactNode;
  defaultOpen?: boolean;
  status?: "pending" | "in_progress" | "success" | "failed";
  className?: string;
}

export function Task({
  children,
  defaultOpen = false,
  status = "pending",
  className,
}: TaskProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div
      className={cn(
        "border rounded-lg mb-2 overflow-hidden bg-white dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800",
        className,
      )}
    >
      {React.Children.map(children, (child) => {
        if (React.isValidElement(child)) {
          // @ts-ignore
          return React.cloneElement(child, { isOpen, setIsOpen, status });
        }
        return child;
      })}
    </div>
  );
}

interface TaskTriggerProps {
  title: string;
  description?: string;
  isOpen?: boolean;
  setIsOpen?: (value: boolean) => void;
  status?: "pending" | "in_progress" | "success" | "failed";
}

export function TaskTrigger({
  title,
  description,
  isOpen,
  setIsOpen,
  status,
}: TaskTriggerProps) {
  const getStatusIcon = () => {
    switch (status) {
      case "success":
        return <CheckCircle2 className="w-5 h-5 text-green-500" />;
      case "failed":
        return <XCircle className="w-5 h-5 text-red-500" />;
      case "in_progress":
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
      default:
        return <Circle className="w-5 h-5 text-zinc-400" />;
    }
  };

  return (
    <button
      onClick={() => setIsOpen?.(!isOpen)}
      className="w-full flex items-center justify-between p-4 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors text-left"
    >
      <div className="flex items-center gap-3">
        {getStatusIcon()}
        <div>
          <div className="font-medium text-sm text-zinc-900 dark:text-zinc-100">
            {title}
          </div>
          {description && (
            <div className="text-xs text-zinc-500 dark:text-zinc-400">
              {description}
            </div>
          )}
        </div>
      </div>
      <ChevronDown
        className={cn(
          "w-4 h-4 text-zinc-400 transition-transform duration-200",
          isOpen && "transform rotate-180",
        )}
      />
    </button>
  );
}

interface TaskContentProps {
  children: React.ReactNode;
  isOpen?: boolean;
}

export function TaskContent({ children, isOpen }: TaskContentProps) {
  return (
    <AnimatePresence initial={false}>
      {isOpen && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="overflow-hidden"
        >
          <div className="p-4 pt-0 border-t border-zinc-100 dark:border-zinc-800/50">
            <div className="flex flex-col gap-2 pt-4">{children}</div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export function TaskItem({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "text-sm text-zinc-600 dark:text-zinc-300 flex items-start gap-2",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function TaskItemFile({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-1 rounded bg-zinc-100 dark:bg-zinc-800 text-xs font-medium text-zinc-700 dark:text-zinc-300",
        className,
      )}
    >
      {children}
    </div>
  );
}
