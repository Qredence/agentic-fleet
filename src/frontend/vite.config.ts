import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import path from "path";
import { defineConfig } from "vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/v1": {
        target: process.env.VITE_API_URL || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: path.resolve(__dirname, "../agentic_fleet/ui"),
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks: {
          // Core React libraries
          "vendor-react": ["react", "react-dom", "react/jsx-runtime"],
          // State management
          "vendor-state": ["zustand", "@tanstack/react-query"],
          // UI component library (radix-ui primitives)
          "vendor-ui": [
            "@radix-ui/react-avatar",
            "@radix-ui/react-collapsible",
            "@radix-ui/react-hover-card",
            "@radix-ui/react-slot",
            "@radix-ui/react-tooltip",
          ],
          // Markdown rendering
          "vendor-markdown": [
            "react-markdown",
            "remark-gfm",
            "remark-breaks",
            "marked",
          ],
          // Syntax highlighting for code blocks
          "vendor-syntax": ["react-syntax-highlighter", "shiki"],
          // Icons and animations
          "vendor-icons": ["lucide-react", "framer-motion", "motion"],
          // Utilities
          "vendor-utils": [
            "clsx",
            "tailwind-merge",
            "class-variance-authority",
          ],
        },
      },
    },
    // Target chunk size of 800KB to accommodate extensive vendor splitting
    chunkSizeWarningLimit: 800,
  },
});
