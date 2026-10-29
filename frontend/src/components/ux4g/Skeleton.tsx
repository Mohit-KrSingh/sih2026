import React from "react";

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  width?: string | number;
  height?: string | number;
  radius?: "none" | "s" | "m" | "l" | "full";
  className?: string;
}

/**
 * UX4G Skeleton Loader Component
 * Placeholder skeleton with subtle pulse animation during data fetching.
 */
export const Skeleton: React.FC<SkeletonProps> = ({
  width = "100%",
  height = "1rem",
  radius = "m",
  className = "",
  style,
  ...props
}) => {
  const radiusClass = {
    none: "rounded-none",
    s: "rounded",
    m: "rounded-md",
    l: "rounded-lg",
    full: "rounded-full",
  }[radius];

  const parsedWidth = typeof width === "number" ? `${width}px` : width;
  const parsedHeight = typeof height === "number" ? `${height}px` : height;

  return (
    <div
      role="status"
      aria-label="Loading..."
      className={`animate-pulse ux4g-bg-neutral-subtle ${radiusClass} ${className}`.trim()}
      style={{
        width: parsedWidth,
        height: parsedHeight,
        ...style,
      }}
      {...props}
    >
      <span className="sr-only">Loading...</span>
    </div>
  );
};
