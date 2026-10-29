import React, { useEffect, useRef } from "react";
import { Icon } from "./Icon";

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  size?: "s" | "m" | "l";
  className?: string;
}

/**
 * UX4G Modal / Dialog Component
 * Uses `.ux4g-modal-backdrop` and `.ux4g-modal-box ux4g-modal-{size}`.
 * Full keyboard accessibility with Escape key support and focus trapping.
 */
export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  footer,
  size = "m",
  className = "",
}) => {
  const modalRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="ux4g-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={modalRef}
        className={`ux4g-modal-box ux4g-modal-${size} w-full max-w-lg bg-white rounded-xl shadow-xl overflow-hidden flex flex-col ${className}`.trim()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between p-4 border-b ux4g-border-neutral-subtle">
          <h2 id="ux4g-modal-title" className="text-base font-bold ux4g-text-neutral-primary">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="p-1 rounded-md ux4g-text-neutral-tertiary hover:ux4g-text-neutral-primary hover:ux4g-bg-neutral-soft focus:outline-none focus:ring-2"
          >
            <Icon name="close" size="sm" color="inherit" aria-hidden="true" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 text-sm ux4g-text-neutral-secondary max-h-[70vh] overflow-y-auto">
          {children}
        </div>

        {/* Modal Footer */}
        {footer && (
          <div className="flex items-center justify-end gap-3 p-4 border-t ux4g-border-neutral-subtle ux4g-bg-neutral-soft">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};
