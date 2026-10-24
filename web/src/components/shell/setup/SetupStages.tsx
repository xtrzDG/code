"use client";

import { Stagger, StaggerItem } from "@/components/motion";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

const STAGES: readonly { title: MessageKey; description: MessageKey }[] = [
  { title: "setup.stages.business.title", description: "setup.stages.business.description" },
  { title: "setup.stages.rules.title", description: "setup.stages.rules.description" },
  { title: "setup.stages.meet.title", description: "setup.stages.meet.description" },
];

/** The three stages of creating the assistant, standing one after another like a corridor. */
export function SetupStages() {
  const { t } = useI18n();
  return (
    <Stagger as="ol" tone="landing" onMount delay={0.25} aria-label={t("setup.stagesLabel")} className="setup-stages relative grid gap-3 sm:grid-cols-3">
      {STAGES.map((stage, index) => (
        <StaggerItem
          key={stage.title}
          as="li"
          depth={index}
          className="setup-stage relative rounded-2xl border border-line bg-surface/80 p-4 backdrop-blur-sm"
        >
          <span
            aria-hidden
            className="mb-3 flex size-8 items-center justify-center rounded-full border border-line bg-surface-muted text-sm font-semibold text-accent"
          >
            {index + 1}
          </span>
          <p className="text-sm font-semibold text-ink">{t(stage.title)}</p>
          <p className="mt-1 text-sm text-ink-muted">{t(stage.description)}</p>
        </StaggerItem>
      ))}
    </Stagger>
  );
}
