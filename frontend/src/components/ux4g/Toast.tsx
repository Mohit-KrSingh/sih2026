import React, { useState, useCallback } from "react";
import { Alert } from "./Alert";
import { ToastContext, type ToastMessage } from "./ToastContext";

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (toast: Omit<ToastMessage, "id">) => {
      const id = Math.random().toString(36).substring(2, 9);
      const newToast: ToastMessage = { ...toast, id };
      setToasts((prev) => [...prev, newToast]);

      const duration = toast.duration ?? 5000;
      if (duration > 0) {
        setTimeout(() => {
          removeToast(id);
        }, duration);
      }
      return id;
    },
    [removeToast]
  );

  return (
    <ToastContext.Provider value={{ addToast, removeToast }}>
      {children}
      <div
        aria-live="polite"
        aria-atomic="false"
        className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none"
      >
        {toasts.map((t) => (
          <div key={t.id} className="pointer-events-auto shadow-lg">
            <Alert
              variant={t.variant || "info"}
              title={t.title}
              onDismiss={() => removeToast(t.id)}
            >
              {t.message}
            </Alert>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

export interface ToastProps {
  variant?: "info" | "success" | "warning" | "error";
  title?: string;
  children: React.ReactNode;
  onClose?: () => void;
}

export const Toast: React.FC<ToastProps> = ({ variant = "info", title, children, onClose }) => {
  return (
    <div className="shadow-lg max-w-sm w-full">
      <Alert variant={variant} title={title} onDismiss={onClose}>
        {children}
      </Alert>
    </div>
  );
};
