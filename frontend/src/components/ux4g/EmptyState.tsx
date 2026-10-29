import React from "react";
import { Icon } from "./Icon";

export interface EmptyStateProps {
  title: string;
  description: string;
  icon?: string;
  action?: React.ReactNode;
  className?: string;
}

/**
 * UX4G Empty State Component
 * Displayed when data queries return no results or an area is not yet populated.
 */
export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon = "inbox",
  action,
  className = "",
}) => {
  return (
    <div
      role="status"
      className={`ux4g-border ux4g-border-dashed ux4g-border-neutral-subtle rounded-xl p-8 flex flex-col items-center justify-center text-center ux4g-bg-neutral-elevated ${className}`.trim()}
    >
      <div className="w-12 h-12 rounded-full ux4g-bg-neutral-soft flex items-center justify-center mb-3 ux4g-text-neutral-secondary">
        <Icon name={icon} size="lg" color="inherit" aria-hidden="true" />
      </div>
      <h3 className="text-base font-bold ux4g-text-neutral-primary mb-1">{title}</h3>
      <p className="text-sm ux4g-text-neutral-secondary max-w-sm mb-4">{description}</p>
      {action && <div className="mt-1">{action}</div>}
    </div>
  );
};
