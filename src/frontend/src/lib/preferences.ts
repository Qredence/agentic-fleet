/**
 * LocalStorage preference utilities.
 *
 * Provides type-safe helpers for reading/writing UI preferences
 * with SSR-safe fallbacks.
 */

const UI_PREFERENCE_KEYS = {
  showTrace: "agenticfleet:ui:showTrace",
  showRawReasoning: "agenticfleet:ui:showRawReasoning",
  executionMode: "agenticfleet:ui:executionMode",
  enableGepa: "agenticfleet:ui:enableGepa",
} as const;

function getStorage(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function readBoolPreference(key: string, fallback: boolean): boolean {
  const storage = getStorage();
  if (!storage) return fallback;
  const raw = storage.getItem(key);
  if (raw === null) return fallback;
  if (raw === "1" || raw === "true") return true;
  if (raw === "0" || raw === "false") return false;
  return fallback;
}

function writeBoolPreference(key: string, value: boolean): void {
  const storage = getStorage();
  if (!storage) return;
  try {
    storage.setItem(key, value ? "1" : "0");
  } catch {
    // Ignore quota / privacy mode errors
  }
}

function readStringPreference(key: string, fallback: string): string {
  const storage = getStorage();
  if (!storage) return fallback;
  const raw = storage.getItem(key);
  return raw ?? fallback;
}

function writeStringPreference(key: string, value: string): void {
  const storage = getStorage();
  if (!storage) return;
  try {
    storage.setItem(key, value);
  } catch {
    // Ignore quota / privacy mode errors
  }
}

export {
  UI_PREFERENCE_KEYS,
  readBoolPreference,
  writeBoolPreference,
  readStringPreference,
  writeStringPreference,
};
