import React from "react";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "solid" | "outline";
  orientation?: "vertical" | "horizontal";
}

/**
 * UX4G Card Component
 * Uses `.ux4g-card ux4g-card-{variant} ux4g-card-{orientation}`.
 */
export const Card: React.FC<CardProps> = ({
  variant = "solid",
  orientation = "vertical",
  className = "",
  children,
  ...props
}) => {
  return (
    <div
      className={`ux4g-card ux4g-card-${variant} ux4g-card-${orientation} overflow-hidden ${className}`.trim()}
      {...props}
    >
      {children}
    </div>
  );
};

export const CardHeader: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className = "",
  children,
  ...props
}) => {
  return (
    <div className={`p-4 border-b ux4g-border-neutral-subtle ${className}`.trim()} {...props}>
      {children}
    </div>
  );
};

export const CardTitle: React.FC<React.HTMLAttributes<HTMLHeadingElement>> = ({
  className = "",
  children,
  ...props
}) => {
  return (
    <h3 className={`text-base font-bold ux4g-text-neutral-primary ${className}`.trim()} {...props}>
      {children}
    </h3>
  );
};

export const CardBody: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className = "",
  children,
  ...props
}) => {
  return (
    <div className={`ux4g-card-body p-4 ${className}`.trim()} {...props}>
      {children}
    </div>
  );
};

export const CardFooter: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className = "",
  children,
  ...props
}) => {
  return (
    <div
      className={`p-4 border-t ux4g-border-neutral-subtle ux4g-bg-neutral-soft flex items-center justify-between ${className}`.trim()}
      {...props}
    >
      {children}
    </div>
  );
};
