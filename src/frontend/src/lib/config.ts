/** API Configuration */
const RAW_API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const NORMALIZED_API_URL = RAW_API_URL.replace(/\/$/, "");

// Ensure the frontend always targets the backend's /api prefix without double-appending
export const API_BASE_URL = NORMALIZED_API_URL.endsWith("/api")
  ? NORMALIZED_API_URL
  : `${NORMALIZED_API_URL}/api`;

/** Frontend base URL */
export const FRONTEND_BASE_URL =
  import.meta.env.VITE_FRONTEND_BASE_URL || "http://localhost:5173";
