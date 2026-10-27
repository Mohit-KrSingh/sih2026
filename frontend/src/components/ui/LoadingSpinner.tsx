interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  label?: string;
  className?: string;
}

export function LoadingSpinner({ size = "md", label, className = "" }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: "w-4 h-4 border-2",
    md: "w-6 h-6 border-2",
    lg: "w-10 h-10 border-3",
  }[size];

  return (
    <div
      role="status"
      aria-live="polite"
      className={`inline-flex items-center gap-2 text-slate-600 ${className}`}
    >
      <div
        className={`${sizeClasses} border-slate-300 border-t-blue-700 rounded-full animate-spin`}
        aria-hidden="true"
      />
      {label && <span className="text-sm font-medium">{label}</span>}
      <span className="sr-only">{label || "Loading"}</span>
    </div>
  );
}
