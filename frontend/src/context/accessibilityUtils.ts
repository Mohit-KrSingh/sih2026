import { createContext, useContext } from "react";

export type TextSize = "normal" | "large" | "x-large";
export type ThemeMode = "light" | "dark";

export interface AccessibilitySettings {
  textSize: TextSize;
  highContrast: boolean;
  theme: ThemeMode;
  underlineLinks: boolean;
  reduceMotion: boolean;
}

export interface AccessibilityContextValue extends AccessibilitySettings {
  setTextSize: (size: TextSize) => void;
  setHighContrast: (enabled: boolean) => void;
  setTheme: (theme: ThemeMode) => void;
  setUnderlineLinks: (enabled: boolean) => void;
  setReduceMotion: (enabled: boolean) => void;
  resetToDefaults: () => void;
  isPanelOpen: boolean;
  openPanel: () => void;
  closePanel: () => void;
  togglePanel: () => void;
}

export const STORAGE_KEY = "edutrace_a11y_settings";

export function getSystemTheme(): ThemeMode {
  try {
    if (typeof window !== "undefined" && window.matchMedia) {
      return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
  } catch {
    // Media query check fallback
  }
  return "light";
}

export function getSystemReducedMotion(): boolean {
  try {
    if (typeof window !== "undefined" && window.matchMedia) {
      return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }
  } catch {
    // Media query check fallback
  }
  return false;
}

export function loadInitialSettings(): AccessibilitySettings {
  const defaults: AccessibilitySettings = {
    textSize: "normal",
    highContrast: false,
    theme: getSystemTheme(),
    underlineLinks: false,
    reduceMotion: getSystemReducedMotion(),
  };

  try {
    if (typeof window !== "undefined" && window.localStorage) {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        return {
          textSize:
            parsed.textSize === "large" || parsed.textSize === "x-large"
              ? parsed.textSize
              : "normal",
          highContrast: Boolean(parsed.highContrast),
          theme:
            parsed.theme === "dark" || parsed.theme === "light"
              ? parsed.theme
              : defaults.theme,
          underlineLinks: Boolean(parsed.underlineLinks),
          reduceMotion:
            typeof parsed.reduceMotion === "boolean"
              ? parsed.reduceMotion
              : defaults.reduceMotion,
        };
      }
    }
  } catch {
    // Gracefully fallback to defaults if storage is blocked or throws
  }

  return defaults;
}

export function saveSettings(settings: AccessibilitySettings): void {
  try {
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    }
  } catch {
    // Storage quota or security error ignored
  }
}

export function applyDomSettings(settings: AccessibilitySettings): void {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.setAttribute("data-theme", settings.theme);
  root.setAttribute("data-text-size", settings.textSize);
  root.setAttribute("data-contrast", settings.highContrast ? "high" : "normal");
  root.setAttribute("data-underline-links", settings.underlineLinks ? "true" : "false");
  root.setAttribute("data-reduced-motion", settings.reduceMotion ? "true" : "false");
}

const defaultContextValue: AccessibilityContextValue = {
  textSize: "normal",
  highContrast: false,
  theme: "light",
  underlineLinks: false,
  reduceMotion: false,
  setTextSize: () => {},
  setHighContrast: () => {},
  setTheme: () => {},
  setUnderlineLinks: () => {},
  setReduceMotion: () => {},
  resetToDefaults: () => {},
  isPanelOpen: false,
  openPanel: () => {},
  closePanel: () => {},
  togglePanel: () => {},
};

export const AccessibilityContext = createContext<AccessibilityContextValue>(defaultContextValue);

export function useAccessibility(): AccessibilityContextValue {
  return useContext(AccessibilityContext);
}
