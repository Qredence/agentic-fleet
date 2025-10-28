import { ReactNode } from "react";
import { motion } from "framer-motion";

interface ChatLayoutProps {
  children: ReactNode;
  sidebar?: ReactNode;
  header?: ReactNode;
}

/**
 * Chat-specific layout with optional sidebar and header
 * Uses framer-motion for smooth animations
 */
export function ChatLayout({ children, sidebar, header }: ChatLayoutProps) {
  return (
    <div className="flex h-full w-full">
      {sidebar && (
        <motion.aside
          initial={{ x: -20, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ duration: 0.3 }}
          className="w-64 border-r border-border bg-card"
        >
          {sidebar}
        </motion.aside>
      )}
      <div className="flex flex-1 flex-col">
        {header && (
          <motion.header
            initial={{ y: -20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.3 }}
            className="border-b border-border bg-card"
          >
            {header}
          </motion.header>
        )}
        <motion.main
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="flex-1 overflow-hidden"
        >
          {children}
        </motion.main>
      </div>
    </div>
  );
}
