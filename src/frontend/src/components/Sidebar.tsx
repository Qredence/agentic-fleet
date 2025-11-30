import { useState } from "react";
import {
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  MessageSquare,
  Search,
  Grid,
  Settings,
} from "lucide-react";
import { clsx } from "clsx";

export const Sidebar = () => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <div
      className={clsx(
        "h-screen bg-gray-1000 border-r border-gray-800 flex flex-col transition-all duration-300 ease-in-out",
        isCollapsed ? "w-16" : "w-[260px]",
      )}
    >
      <div className="p-3 flex items-center justify-between">
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-md transition-colors"
        >
          {isCollapsed ? (
            <PanelLeftOpen size={20} />
          ) : (
            <PanelLeftClose size={20} />
          )}
        </button>
        {!isCollapsed && (
          <button className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-md transition-colors">
            <Search size={20} />
          </button>
        )}
      </div>

      <div className="px-3 py-2">
        <button
          className={clsx(
            "flex items-center gap-2 w-full p-2 text-gray-100 hover:bg-gray-800 rounded-md transition-colors border border-gray-800",
            isCollapsed ? "justify-center" : "justify-start",
          )}
        >
          <Plus size={16} />
          {!isCollapsed && (
            <span className="text-sm font-medium">New Chat</span>
          )}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto py-2 px-3 space-y-1">
        {[1, 2, 3].map((i) => (
          <button
            key={i}
            className={clsx(
              "flex items-center gap-3 w-full p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-md transition-colors text-left group",
              isCollapsed ? "justify-center" : "justify-start",
            )}
          >
            <MessageSquare size={16} />
            {!isCollapsed && (
              <span className="text-sm truncate">Previous Chat {i}</span>
            )}
          </button>
        ))}
      </div>

      <div className="p-3 border-t border-gray-800 space-y-1">
        <button
          className={clsx(
            "flex items-center gap-3 w-full p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-md transition-colors",
            isCollapsed ? "justify-center" : "justify-start",
          )}
        >
          <Grid size={18} />
          {!isCollapsed && <span className="text-sm">Apps</span>}
        </button>
        <button
          className={clsx(
            "flex items-center gap-3 w-full p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-md transition-colors",
            isCollapsed ? "justify-center" : "justify-start",
          )}
        >
          <Settings size={18} />
          {!isCollapsed && <span className="text-sm">Settings</span>}
        </button>
      </div>
    </div>
  );
};
