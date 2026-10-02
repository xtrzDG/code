"use client";

import { useEffect, useRef } from "react";

import type { ProfileWizardStep, WizardStepView } from "@/api/types";
import { IconCheck } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

/** The six steps with their completion; a step can be opened at any time. */
export function StepNavigation({
  steps,
  activeStep,
  onSelect,
}: {
  steps: readonly WizardStepView[];
  activeStep: ProfileWizardStep;
  onSelect: (step: ProfileWizardStep) => void;
}) {
  const { t } = useI18n();
  const listRef = useRef<HTMLOListElement>(null);

  // On phones the steps scroll sideways: keep the open one in view.
  useEffect(() => {
    const list = listRef.current;
    const current = list?.querySelector<HTMLElement>('[aria-current="step"]');
    if (!list || !current || list.scrollWidth <= list.clientWidth) {
      return;
    }
    const listBox = list.getBoundingClientRect();
    const itemBox = current.getBoundingClientRect();
    if (itemBox.left < listBox.left || itemBox.right > listBox.right) {
      list.scrollBy({ left: itemBox.left - listBox.left - 16, behavior: "smooth" });
    }
  }, [activeStep]);

  return (
    <nav aria-label={t("onboarding.stepsLabel")}>
      <ol ref={listRef} className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 lg:mx-0 lg:flex-col lg:gap-1 lg:overflow-visible lg:px-0">
        {steps.map((step) => {
          const isActive = step.step === activeStep;
          return (
            <li key={step.step} className="shrink-0 lg:shrink">
              <button
                type="button"
                onClick={() => onSelect(step.step)}
                aria-current={isActive ? "step" : undefined}
                className={cn(
                  // relative: the sr-only status must not widen the page past the scrolling list.
                  "relative flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-start text-sm transition-colors",
                  isActive ? "bg-accent-soft text-accent-ink" : "text-ink-muted hover:bg-surface-muted hover:text-ink",
                )}
              >
                <span
                  className={cn(
                    "flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold",
                    step.is_complete
                      ? "bg-success-soft text-success"
                      : isActive
                        ? "bg-accent-solid text-on-accent"
                        : "bg-surface-muted text-ink-muted ring-1 ring-line",
                  )}
                >
                  {step.is_complete ? <IconCheck className="size-4" aria-hidden /> : step.number}
                </span>
                <span className="min-w-0">
                  <span className="block font-medium whitespace-nowrap lg:whitespace-normal">{step.title}</span>
                  <span className="sr-only">
                    {" — "}
                    {step.is_complete ? t("onboarding.complete") : t("onboarding.incomplete")}
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
