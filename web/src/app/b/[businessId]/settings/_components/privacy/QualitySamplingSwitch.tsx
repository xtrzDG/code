"use client";

import { useId, type ReactNode } from "react";

import { Switch } from "@/components/content/Switch";
import { useI18n } from "@/i18n/client";

/**
 * Settings → Privacy: whether the nightly quality sample may read a few of
 * the business's real conversations (scored by the same AI provider that
 * writes the answers). Part of the retention form, which saves it at once.
 */
export function QualitySamplingSwitch({
  checked,
  status,
  onChange,
}: {
  checked: boolean;
  status: ReactNode;
  onChange: (allowed: boolean) => void;
}) {
  const { t } = useI18n();
  const hintId = useId();
  const label = t("privacyRetention.qualitySampling.label");

  return (
    <div className="flex items-start justify-between gap-4 border-t border-line pt-5" data-testid="quality-sampling">
      <div className="min-w-0 space-y-1">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <p className="text-sm font-medium text-ink">{label}</p>
          {status}
        </div>
        <p id={hintId} className="max-w-3xl text-sm text-ink-muted">
          {t("privacyRetention.qualitySampling.hint")}
        </p>
      </div>
      <Switch checked={checked} onChange={onChange} label={label} describedBy={hintId} />
    </div>
  );
}
