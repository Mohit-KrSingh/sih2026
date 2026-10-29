import React from "react";
import { Link as RouterLink } from "react-router-dom";
import { Icon } from "./Icon";

export interface SidebarItem {
  id: string;
  label: string;
  href: string;
  icon?: string;
  active?: boolean;
  badge?: React.ReactNode;
}

export interface SidebarSection {
  title?: string;
  items: SidebarItem[];
}

export interface SidebarProps {
  sections: SidebarSection[];
  ariaLabel?: string;
  className?: string;
}

/**
 * UX4G Sidebar Component
 * Semantic `<aside role="navigation">` for role-aware application navigation.
 */
export const Sidebar: React.FC<SidebarProps> = ({
  sections,
  ariaLabel = "Sidebar Navigation",
  className = "",
}) => {
  return (
    <aside
      role="navigation"
      aria-label={ariaLabel}
      className={`w-64 border-r ux4g-border-neutral-subtle ux4g-bg-neutral-elevated min-h-screen p-4 flex flex-col gap-6 ${className}`.trim()}
    >
      {sections.map((section, sIdx) => (
        <div key={sIdx} className="flex flex-col gap-1.5">
          {section.title && (
            <h3 className="px-3 text-xs font-bold uppercase tracking-wider ux4g-text-neutral-tertiary mb-1">
              {section.title}
            </h3>
          )}
          <ul className="space-y-1">
            {section.items.map((item) => (
              <li key={item.id}>
                <RouterLink
                  to={item.href}
                  aria-current={item.active ? "page" : undefined}
                  className={`flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    item.active
                      ? "ux4g-bg-primary-soft ux4g-text-brand-primary font-semibold"
                      : "ux4g-text-neutral-secondary hover:ux4g-bg-neutral-soft hover:ux4g-text-neutral-primary"
                  }`}
                >
                  <div className="flex items-center gap-2.5 truncate">
                    {item.icon && (
                      <Icon
                        name={item.icon}
                        size="sm"
                        color={item.active ? "primary" : "neutral"}
                        aria-hidden="true"
                      />
                    )}
                    <span className="truncate">{item.label}</span>
                  </div>
                  {item.badge && <span className="ml-2 shrink-0">{item.badge}</span>}
                </RouterLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </aside>
  );
};
