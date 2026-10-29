import { createContext, useContext } from "react";

export interface ToastMessage {
  id: string;
  variant?: "info" | "success" | "warning" | "error";
  title?: string;
  message: string;
  duration?: number;
}

export interface ToastContextType {
  addToast: (toast: Omit<ToastMessage, "id">) => string;
  removeToast: (id: string) => void;
}

export const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const useToast = (): ToastContextType => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
};
