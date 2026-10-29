import React from "react";
import { Icon } from "./Icon";

export interface StepItem {
  title: string;
  description?: string;
}

export interface StepperProps {
  steps: StepItem[];
  currentStep: number; // 0-based
  orientation?: "horizontal" | "vertical";
  className?: string;
}

/**
 * UX4G Stepper Component
 * Uses `.ux4g-stepper ux4g-stepper-{orientation}` with semantic step states.
 */
export const Stepper: React.FC<StepperProps> = ({
  steps,
  currentStep,
  orientation = "horizontal",
  className = "",
}) => {
  return (
    <nav
      aria-label="Progress Stepper"
      className={`ux4g-stepper ux4g-stepper-${orientation} w-full ${className}`.trim()}
    >
      <ol
        className={`flex ${
          orientation === "horizontal"
            ? "items-center justify-between gap-2"
            : "flex-col gap-4"
        } w-full`}
      >
        {steps.map((step, index) => {
          const isCompleted = index < currentStep;
          const isCurrent = index === currentStep;

          return (
            <li
              key={index}
              aria-current={isCurrent ? "step" : undefined}
              className={`ux4g-stepper-step flex ${
                orientation === "horizontal" ? "flex-1 items-center" : "items-start gap-3"
              }`}
            >
              <div className="flex items-center gap-3">
                <span
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold shrink-0 transition-colors ${
                    isCompleted
                      ? "ux4g-bg-primary-strong ux4g-text-white"
                      : isCurrent
                      ? "border-2 ux4g-border-primary ux4g-bg-primary-soft ux4g-text-brand-primary"
                      : "border-2 ux4g-border-neutral-subtle ux4g-text-neutral-tertiary ux4g-bg-neutral-elevated"
                  }`}
                >
                  {isCompleted ? (
                    <Icon name="check" size="xs" color="inherit" aria-hidden="true" />
                  ) : (
                    <span>{index + 1}</span>
                  )}
                </span>
                <div className="min-w-0">
                  <p
                    className={`text-sm font-medium leading-none ${
                      isCurrent
                        ? "ux4g-text-brand-primary font-semibold"
                        : isCompleted
                        ? "ux4g-text-neutral-primary"
                        : "ux4g-text-neutral-tertiary"
                    }`}
                  >
                    {step.title}
                  </p>
                  {step.description && (
                    <p className="text-xs ux4g-text-neutral-tertiary mt-0.5">{step.description}</p>
                  )}
                </div>
              </div>

              {orientation === "horizontal" && index < steps.length - 1 && (
                <div
                  className={`flex-1 h-0.5 mx-4 transition-colors ${
                    isCompleted ? "ux4g-bg-primary-strong" : "ux4g-bg-neutral-subtle"
                  }`}
                  aria-hidden="true"
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
};
