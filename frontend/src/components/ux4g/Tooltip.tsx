import React, { useState, useId } from "react";

export interface TooltipProps {
  content: React.ReactNode;
  placement?:
    | "top-center"
    | "top-left"
    | "top-right"
    | "bottom-center"
    | "bottom-left"
    | "bottom-right"
    | "left-center"
    | "right-center";
  size?: "s" | "xs";
  children: React.ReactElement;
  className?: string;
}

/**
 * UX4G Tooltip Component
 * Uses `.ux4g-tooltip-wrapper` and `.ux4g-tooltip ux4g-tooltip-{placement} ux4g-tooltip-{size}`.
 */
export const Tooltip: React.FC<TooltipProps> = ({
  content,
  placement = "top-center",
  size = "s",
  children,
  className = "",
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const tooltipId = useId();

  return (
    <span
      className={`ux4g-tooltip-wrapper inline-block relative ${className}`.trim()}
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
      onFocus={() => setIsVisible(true)}
      onBlur={() => setIsVisible(false)}
      onKeyDown={(e) => {
        if (e.key === "Escape") setIsVisible(false);
      }}
    >
      {React.cloneElement(children, {
        "aria-describedby": isVisible ? tooltipId : undefined,
      })}
      <span
        id={tooltipId}
        role="tooltip"
        className={`ux4g-tooltip ux4g-tooltip-${placement} ux4g-tooltip-${size}`}
        style={{
          display: isVisible ? "flex" : undefined,
          opacity: isVisible ? 1 : undefined,
        }}
      >
        {content}
      </span>
    </span>
  );
};
