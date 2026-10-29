import React, { useEffect, useState, useCallback } from "react";
import {
  AccessibilityContext,
  AccessibilitySettings,
  AccessibilityContextValue,
  STORAGE_KEY,
  TextSize,
  ThemeMode,
  applyDomSettings,
  getSystemReducedMotion,
  getSystemTheme,
  loadInitialSettings,
  saveSettings,
} from "./accessibilityUtils";

export interface AccessibilityProviderProps {
  children: React.ReactNode;
  initialSettings?: Partial<AccessibilitySettings>;
}

export const AccessibilityProvider: React.FC<AccessibilityProviderProps> = ({
  children,
  initialSettings,
}) => {
  const [settings, setSettings] = useState<AccessibilitySettings>(() => {
    const loaded = loadInitialSettings();
    return initialSettings ? { ...loaded, ...initialSettings } : loaded;
  });

  const [isPanelOpen, setIsPanelOpen] = useState(false);

  // Apply settings to DOM and persist on change
  useEffect(() => {
    applyDomSettings(settings);
    saveSettings(settings);
  }, [settings]);

  // Listen for system theme and motion changes if user hasn't explicitly customized
  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;

    try {
      const colorQuery = window.matchMedia("(prefers-color-scheme: dark)");
      const handleColorChange = (e: MediaQueryListEvent) => {
        try {
          const stored = window.localStorage.getItem(STORAGE_KEY);
          if (!stored) {
            setSettings((prev) => ({ ...prev, theme: e.matches ? "dark" : "light" }));
          }
        } catch {
          // ignore
        }
      };

      const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
      const handleMotionChange = (e: MediaQueryListEvent) => {
        try {
          const stored = window.localStorage.getItem(STORAGE_KEY);
          if (!stored) {
            setSettings((prev) => ({ ...prev, reduceMotion: e.matches }));
          }
        } catch {
          // ignore
        }
      };

      if (colorQuery.addEventListener) {
        colorQuery.addEventListener("change", handleColorChange);
        motionQuery.addEventListener("change", handleMotionChange);
        return () => {
          colorQuery.removeEventListener("change", handleColorChange);
          motionQuery.removeEventListener("change", handleMotionChange);
        };
      }
    } catch {
      // ignore
    }
  }, []);

  const setTextSize = useCallback((textSize: TextSize) => {
    setSettings((prev) => ({ ...prev, textSize }));
  }, []);

  const setHighContrast = useCallback((highContrast: boolean) => {
    setSettings((prev) => ({ ...prev, highContrast }));
  }, []);

  const setTheme = useCallback((theme: ThemeMode) => {
    setSettings((prev) => ({ ...prev, theme }));
  }, []);

  const setUnderlineLinks = useCallback((underlineLinks: boolean) => {
    setSettings((prev) => ({ ...prev, underlineLinks }));
  }, []);

  const setReduceMotion = useCallback((reduceMotion: boolean) => {
    setSettings((prev) => ({ ...prev, reduceMotion }));
  }, []);

  const resetToDefaults = useCallback(() => {
    const freshDefaults: AccessibilitySettings = {
      textSize: "normal",
      highContrast: false,
      theme: getSystemTheme(),
      underlineLinks: false,
      reduceMotion: getSystemReducedMotion(),
    };
    setSettings(freshDefaults);
  }, []);

  const openPanel = useCallback(() => setIsPanelOpen(true), []);
  const closePanel = useCallback(() => setIsPanelOpen(false), []);
  const togglePanel = useCallback(() => setIsPanelOpen((prev) => !prev), []);

  const value: AccessibilityContextValue = {
    ...settings,
    setTextSize,
    setHighContrast,
    setTheme,
    setUnderlineLinks,
    setReduceMotion,
    resetToDefaults,
    isPanelOpen,
    openPanel,
    closePanel,
    togglePanel,
  };

  return (
    <AccessibilityContext.Provider value={value}>
      {children}
    </AccessibilityContext.Provider>
  );
};
