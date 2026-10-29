import React, { useState } from "react";
import { Icon } from "./Icon";

export interface AccordionItemData {
  id: string;
  title: string;
  content: React.ReactNode;
  disabled?: boolean;
}

export interface AccordionProps {
  items: AccordionItemData[];
  allowMultiple?: boolean;
  defaultExpandedIds?: string[];
  className?: string;
}

/**
 * UX4G Accordion Component
 * Uses `.ux4g-accordion ux4g-accordion-arrow-right` with accessible ARIA expansion attributes.
 */
export const Accordion: React.FC<AccordionProps> = ({
  items,
  allowMultiple = false,
  defaultExpandedIds = [],
  className = "",
}) => {
  const [expandedIds, setExpandedIds] = useState<string[]>(defaultExpandedIds);

  const toggleItem = (id: string) => {
    if (allowMultiple) {
      setExpandedIds((prev) =>
        prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
      );
    } else {
      setExpandedIds((prev) => (prev.includes(id) ? [] : [id]));
    }
  };

  return (
    <div className={`ux4g-accordion ux4g-accordion-arrow-right ux4g-border ux4g-border-neutral-subtle rounded-lg overflow-hidden ${className}`.trim()}>
      {items.map((item) => {
        const isExpanded = expandedIds.includes(item.id);

        return (
          <div key={item.id} className="ux4g-accordion__item border-b ux4g-border-neutral-subtle last:border-b-0">
            <h3 className="ux4g-accordion__header m-0">
              <button
                type="button"
                id={`accordion-btn-${item.id}`}
                aria-expanded={isExpanded}
                aria-controls={`accordion-panel-${item.id}`}
                disabled={item.disabled}
                onClick={() => toggleItem(item.id)}
                className={`ux4g-accordion__button w-full px-4 py-3 flex items-center justify-between text-left text-sm font-semibold transition-colors ${
                  isExpanded ? "ux4g-bg-neutral-soft ux4g-text-brand-primary" : "ux4g-bg-neutral-elevated ux4g-text-neutral-primary hover:ux4g-bg-neutral-soft"
                } ${item.disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
              >
                <span>{item.title}</span>
                <span
                  className={`transform transition-transform duration-200 flex items-center ${
                    isExpanded ? "rotate-180" : ""
                  }`}
                >
                  <Icon name="expand_more" size="sm" color="inherit" aria-hidden="true" />
                </span>
              </button>
            </h3>
            {isExpanded && (
              <div
                id={`accordion-panel-${item.id}`}
                role="region"
                aria-labelledby={`accordion-btn-${item.id}`}
                className="ux4g-accordion__collapse"
              >
                <div className="ux4g-accordion__body p-4 ux4g-bg-neutral-elevated text-sm ux4g-text-neutral-secondary border-t ux4g-border-neutral-subtle">
                  {item.content}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
