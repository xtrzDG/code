"use client";

import { useId } from "react";

import { Switch } from "@/components/content/Switch";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { qualitySamplingBody, type PrivacySettingsView } from "../../_lib/privacySettings";
import type { PrivacySettingsState } from "../../_lib/usePrivacySettings";

/**
 * Settings → Privacy: whether the nightly quality sample may read a few of
 * the business's real conversations (scored by the same AI provider that
 * writes the answers). It saves at once; the retention periods stay.
 */
export function QualitySamplingSwitch({ stored, state }: { stored: PrivacySettingsView; state: PrivacySettingsState }) {
  const { t } = useI18n();
  const toast = useToast();
  const hintId = useId();
  const { settings, save } = state;
  const label = t("privacyRetention.qualitySampling.label");

  const change = async (allowed: boolean) => {
    const result = await save.run(qualitySamplingBody(stored, allowed));
    if (result.ok) {
      settings.setData(result.data);
      toast.success(t(allowed ? "privacyRetention.qualitySampling.on" : "privacyRetention.qualitySampling.off"));
    } else {
      toast.error(result.error);
    }
  };

  return (
    <div className="flex items-start justify-between gap-4 border-t border-line pt-5" data-testid="quality-sampling">
      <div className="min-w-0 space-y-1">
        <p className="text-sm font-medium text-ink">{label}</p>
        <p id={hintId} className="max-w-3xl text-sm text-ink-muted">
          {t("privacyRetention.qualitySampling.hint")}
        </p>
      </div>
      <Switch
        checked={stored.quality_sampling_allowed}
        onChange={(allowed) => void change(allowed)}
        label={label}
        describedBy={hintId}
        disabled={save.isPending}
      />
    </div>
  );
}
