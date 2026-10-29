import React from "react";
import { Link as RouterLink } from "react-router-dom";

export interface LinkProps extends React.AnchorHTMLAttributes<HTMLAnchorElement> {
  size?: "sm" | "md";
  variant?: "default" | "neutral";
  to?: string;
  isExternal?: boolean;
}

/**
 * UX4G Link Component
 * Uses `.ux4g-text-link-{size}` classes.
 */
export const Link = React.forwardRef<HTMLAnchorElement, LinkProps>(
  (
    {
      size = "md",
      variant = "default",
      to,
      href,
      isExternal = false,
      className = "",
      children,
      ...props
    },
    ref
  ) => {
    const sizeClass = `ux4g-text-link-${size}`;
    const variantClass = variant === "neutral" ? "ux4g-text-neutral-primary" : "";
    const combinedClassName = `${sizeClass} ${variantClass} ${className}`.trim();

    if (to) {
      return (
        <RouterLink ref={ref} to={to} className={combinedClassName} {...(props as any)}>
          {children}
        </RouterLink>
      );
    }

    const externalProps = isExternal
      ? { target: "_blank", rel: "noopener noreferrer" }
      : {};

    return (
      <a
        ref={ref}
        href={href}
        className={combinedClassName}
        {...externalProps}
        {...props}
      >
        {children}
      </a>
    );
  }
);

Link.displayName = "Link";
