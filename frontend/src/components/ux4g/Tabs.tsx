import React, { useState } from "react";

export interface TabItem {
  id: string;
  label: string;
  content: React.ReactNode;
  disabled?: boolean;
  badge?: React.ReactNode;
}

export interface TabsProps {
  items: TabItem[];
  activeId?: string;
  defaultActiveId?: string;
  onChange?: (id: string) => void;
  variant?: "underline" | "pill";
  size?: "sm" | "md" | "lg";
  ariaLabel?: string;
  className?: string;
}

/**
 * UX4G Tabs Component
 * Uses `.ux4g-tab ux4g-tab-{variant} ux4g-tab-{size}` with accessible tablist/tab/tabpanel roles
 * and keyboard navigation support.
 */
export const Tabs: React.FC<TabsProps> = ({
  items,
  activeId: controlledActiveId,
  defaultActiveId,
  onChange,
  variant = "underline",
  size = "md",
  ariaLabel = "Tabs",
  className = "",
}) => {
  const [internalActiveId, setInternalActiveId] = useState<string>(
    defaultActiveId || items[0]?.id || ""
  );

  const activeId = controlledActiveId !== undefined ? controlledActiveId : internalActiveId;

  const handleTabClick = (id: string) => {
    if (controlledActiveId === undefined) {
      setInternalActiveId(id);
    }
    onChange?.(id);
  };

  const handleKeyDown = (e: React.KeyboardEvent, index: number) => {
    const enabledTabs = items.filter((item) => !item.disabled);
    const currentIndex = enabledTabs.findIndex((item) => item.id === items[index].id);

    if (e.key === "ArrowRight") {
      e.preventDefault();
      const nextIndex = (currentIndex + 1) % enabledTabs.length;
      handleTabClick(enabledTabs[nextIndex].id);
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      const prevIndex = (currentIndex - 1 + enabledTabs.length) % enabledTabs.length;
      handleTabClick(enabledTabs[prevIndex].id);
    }
  };

  const currentTab = items.find((item) => item.id === activeId);

  return (
    <div className={`w-full flex flex-col ${className}`.trim()}>
      <div className={`ux4g-tab ux4g-tab-${variant} ux4g-tab-${size}`}>
        <div role="tablist" aria-label={ariaLabel} className="ux4g-tab-list flex gap-4">
          {items.map((item, index) => {
            const isActive = item.id === activeId;

            return (
              <button
                key={item.id}
                role="tab"
                id={`tab-${item.id}`}
                aria-selected={isActive}
                aria-controls={`tabpanel-${item.id}`}
                tabIndex={isActive ? 0 : -1}
                disabled={item.disabled}
                onClick={() => handleTabClick(item.id)}
                onKeyDown={(e) => handleKeyDown(e, index)}
                className={`ux4g-tab-item px-4 py-2.5 text-sm font-medium transition-colors flex items-center gap-2 ${
                  isActive ? "active ux4g-text-brand-primary font-semibold" : "ux4g-text-neutral-secondary hover:ux4g-text-neutral-primary"
                } ${item.disabled ? "opacity-40 cursor-not-allowed" : "cursor-pointer"}`}
              >
                <span>{item.label}</span>
                {item.badge && <span className="ml-1">{item.badge}</span>}
              </button>
            );
          })}
        </div>
      </div>

      <div
        role="tabpanel"
        id={`tabpanel-${currentTab?.id}`}
        aria-labelledby={`tab-${currentTab?.id}`}
        tabIndex={0}
        className="pt-4 outline-none focus:ring-1 focus:ring-primary-500 rounded"
      >
        {currentTab?.content}
      </div>
    </div>
  );
};
