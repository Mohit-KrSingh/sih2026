import React, { useEffect, useRef } from "react";
import { useAccessibility, TextSize, ThemeMode } from "../../context/accessibilityUtils";
import { Button } from "./Button";
import { Icon } from "./Icon";
import { Switch } from "./Switch";

export interface AccessibilityPanelProps {
  className?: string;
}

/**
 * UX4G Accessibility Toolkit Panel (R05)
 *
 * Implements WCAG 2.1 AA and Government of India UX4G digital accessibility requirements:
 * - Text size scaling: Normal (100%), Large (112.5%), Extra Large (125%)
 * - Display theme: Light or Dark mode with system default detection
 * - High contrast toggle: Increases border, text, and container visibility
 * - Underline links toggle: Persistently marks hyperlinks
 * - Reduced motion toggle: Disables animations, smooth scrolling, and transitions
 * - Reset to defaults: Restores system-matched defaults and clears local storage
 * - Dialog semantics: role="dialog", aria-modal="true", keyboard focus trapping, Escape key support
 */
export const AccessibilityPanel: React.FC<AccessibilityPanelProps> = ({ className = "" }) => {
  const {
    textSize,
    setTextSize,
    highContrast,
    setHighContrast,
    theme,
    setTheme,
    underlineLinks,
    setUnderlineLinks,
    reduceMotion,
    setReduceMotion,
    resetToDefaults,
    isPanelOpen,
    closePanel,
  } = useAccessibility();

  const panelRef = useRef<HTMLDivElement | null>(null);
  const previouslyFocusedRef = useRef<HTMLElement | null>(null);

  // Focus management and Escape key handling
  useEffect(() => {
    if (isPanelOpen) {
      previouslyFocusedRef.current = document.activeElement as HTMLElement;

      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === "Escape") {
          e.preventDefault();
          closePanel();
        }

        // Focus trapping inside the panel
        if (e.key === "Tab" && panelRef.current) {
          const focusableElements = panelRef.current.querySelectorAll<HTMLElement>(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
          );
          if (focusableElements.length === 0) return;

          const first = focusableElements[0];
          const last = focusableElements[focusableElements.length - 1];

          if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last.focus();
          } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      };

      document.addEventListener("keydown", handleKeyDown);

      // Focus first element in panel
      const timer = setTimeout(() => {
        if (panelRef.current) {
          const firstFocusable = panelRef.current.querySelector<HTMLElement>(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
          );
          firstFocusable?.focus();
        }
      }, 50);

      return () => {
        document.removeEventListener("keydown", handleKeyDown);
        clearTimeout(timer);
      };
    } else if (previouslyFocusedRef.current) {
      // Restore focus to trigger when panel closes
      previouslyFocusedRef.current.focus();
      previouslyFocusedRef.current = null;
    }
  }, [isPanelOpen, closePanel]);

  if (!isPanelOpen) return null;

  return (
    <div
      role="region"
      aria-label="Accessibility Toolkit Backdrop"
      className="fixed inset-0 z-50 flex justify-end bg-black/40 transition-opacity"
      onClick={(e) => {
        if (e.target === e.currentTarget) closePanel();
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="a11y-toolkit-title"
        className={`w-full max-w-sm sm:max-w-md h-full ux4g-bg-neutral-elevated border-l ux4g-border-neutral-subtle shadow-2xl flex flex-col justify-between overflow-hidden ${className}`.trim()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b ux4g-border-neutral-subtle ux4g-bg-neutral-soft">
          <div className="flex items-center gap-2">
            <Icon name="tune" size="sm" aria-hidden="true" />
            <h2 id="a11y-toolkit-title" className="text-base font-bold ux4g-text-neutral-primary">
              Accessibility Tools
            </h2>
          </div>
          <button
            type="button"
            onClick={closePanel}
            aria-label="Close accessibility tools"
            className="p-1.5 rounded-md ux4g-text-neutral-secondary hover:ux4g-text-neutral-primary hover:ux4g-bg-neutral-subtle focus:outline-none focus:ring-2"
          >
            <Icon name="close" size="sm" aria-hidden="true" />
          </button>
        </div>

        {/* Controls Body */}
        <div className="p-5 space-y-6 overflow-y-auto flex-1 text-sm">
          {/* 1. Text Sizing */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-semibold ux4g-text-neutral-primary">Text Size</span>
              <span className="text-xs ux4g-text-neutral-secondary uppercase font-mono">
                {textSize}
              </span>
            </div>
            <p className="text-xs ux4g-text-neutral-secondary">
              Scale interface font sizing across all pages.
            </p>
            <div
              role="group"
              aria-label="Select text size"
              className="grid grid-cols-3 gap-2 pt-1"
            >
              <Button
                variant={textSize === "normal" ? "primary" : "outline-primary"}
                size="s"
                aria-pressed={textSize === "normal"}
                onClick={() => setTextSize("normal" as TextSize)}
                className="w-full justify-center"
              >
                Normal (100%)
              </Button>
              <Button
                variant={textSize === "large" ? "primary" : "outline-primary"}
                size="s"
                aria-pressed={textSize === "large"}
                onClick={() => setTextSize("large" as TextSize)}
                className="w-full justify-center"
              >
                Large (112%)
              </Button>
              <Button
                variant={textSize === "x-large" ? "primary" : "outline-primary"}
                size="s"
                aria-pressed={textSize === "x-large"}
                onClick={() => setTextSize("x-large" as TextSize)}
                className="w-full justify-center"
              >
                X-Large (125%)
              </Button>
            </div>
          </div>

          <div className="border-t ux4g-border-neutral-subtle" />

          {/* 2. Color Theme */}
          <div className="space-y-2">
            <span className="font-semibold ux4g-text-neutral-primary">Color Theme</span>
            <p className="text-xs ux4g-text-neutral-secondary">
              Select your preferred visual display mode.
            </p>
            <div
              role="group"
              aria-label="Select color theme"
              className="grid grid-cols-2 gap-3 pt-1"
            >
              <Button
                variant={theme === "light" ? "primary" : "outline-primary"}
                size="m"
                aria-pressed={theme === "light"}
                leftIcon={<Icon name="light_mode" size="sm" aria-hidden="true" />}
                onClick={() => setTheme("light" as ThemeMode)}
                className="w-full justify-center"
              >
                Light
              </Button>
              <Button
                variant={theme === "dark" ? "primary" : "outline-primary"}
                size="m"
                aria-pressed={theme === "dark"}
                leftIcon={<Icon name="dark_mode" size="sm" aria-hidden="true" />}
                onClick={() => setTheme("dark" as ThemeMode)}
                className="w-full justify-center"
              >
                Dark
              </Button>
            </div>
          </div>

          <div className="border-t ux4g-border-neutral-subtle" />

          {/* 3. High Contrast Mode */}
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-0.5">
              <label
                htmlFor="a11y-high-contrast"
                className="font-semibold ux4g-text-neutral-primary cursor-pointer select-none"
              >
                High Contrast
              </label>
              <p className="text-xs ux4g-text-neutral-secondary">
                Enhance visual borders, controls, and surface separation.
              </p>
            </div>
            <Switch
              id="a11y-high-contrast"
              label=""
              checked={highContrast}
              onChange={(e) => setHighContrast(e.target.checked)}
              aria-label="Toggle high contrast mode"
            />
          </div>

          <div className="border-t ux4g-border-neutral-subtle" />

          {/* 4. Underline Links */}
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-0.5">
              <label
                htmlFor="a11y-underline-links"
                className="font-semibold ux4g-text-neutral-primary cursor-pointer select-none"
              >
                Underline Links
              </label>
              <p className="text-xs ux4g-text-neutral-secondary">
                Always underline hyperlinks for easier visual identification.
              </p>
            </div>
            <Switch
              id="a11y-underline-links"
              label=""
              checked={underlineLinks}
              onChange={(e) => setUnderlineLinks(e.target.checked)}
              aria-label="Toggle underline links"
            />
          </div>

          <div className="border-t ux4g-border-neutral-subtle" />

          {/* 5. Reduced Motion */}
          <div className="flex items-start justify-between gap-3">
            <div className="space-y-0.5">
              <label
                htmlFor="a11y-reduced-motion"
                className="font-semibold ux4g-text-neutral-primary cursor-pointer select-none"
              >
                Reduce Motion
              </label>
              <p className="text-xs ux4g-text-neutral-secondary">
                Minimize smooth scrolling, transitions, and animations.
              </p>
            </div>
            <Switch
              id="a11y-reduced-motion"
              label=""
              checked={reduceMotion}
              onChange={(e) => setReduceMotion(e.target.checked)}
              aria-label="Toggle reduce motion"
            />
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t ux4g-border-neutral-subtle ux4g-bg-neutral-soft flex items-center justify-between gap-3">
          <Button
            variant="outline-neutral"
            size="m"
            leftIcon={<Icon name="restart_alt" size="sm" aria-hidden="true" />}
            onClick={resetToDefaults}
            title="Reset all accessibility settings to system defaults"
          >
            Reset Defaults
          </Button>

          <Button variant="primary" size="m" onClick={closePanel}>
            Done
          </Button>
        </div>
      </div>
    </div>
  );
};
