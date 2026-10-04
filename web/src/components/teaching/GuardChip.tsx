"use client";

import { IconShield } from "@/components/icons";
import { Badge } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { guardChip, type GuardView } from "@/lib/teaching";

/**
 * What the reply guard did with an assistant answer (R10): corrected once
 * or held back for a person, with why. Nothing for a clean answer.
 */
export function GuardChip({ guard }: { guard: GuardView | null | undefined }) {
  const { t } = useI18n();
  const chip = guardChip(guard);
  if (!chip) {
    return null;
  }
  const reasons = chip.reasons.map((reason) => t(reason)).join(", ");
  return (
    <span className="inline-flex max-w-full flex-wrap items-center gap-1.5" aria-label={t("teaching.guard.label")} role="note">
      <Badge tone={chip.tone} icon={<IconShield className="size-3.5" aria-hidden />}>
        {t(chip.label)}
      </Badge>
      {reasons ? <span className="text-xs text-ink-subtle">{reasons}</span> : null}
    </span>
  );
}
