"use client";

import { useState } from "react";

import { SavePill } from "@/components/forms/SavePill";
import { Card, Field, Input } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { MAX_RETENTION_DAYS, MIN_RETENTION_DAYS } from "../../_lib/general";
import type { GeneralSettings } from "../../_lib/useGeneralSettings";

/**
 * How long call recordings are kept. The number counts when the field is
 * left (or Enter pressed), not on every digit: a shorter period deletes
 * recordings and asks first, so "1" on the way to "120" must not ask.
 */
export function RecordingsCard({ settings }: { settings: GeneralSettings }) {
  const { t } = useI18n();
  const { form, disabled, update, errorText, fieldState, retry } = settings;
  const [draft, setDraft] = useState<string | null>(null);
  const commit = () => {
    if (draft !== null) {
      update("retentionDays", draft);
      setDraft(null);
    }
  };
  return (
    <Card title={t("settings.general.recordingsTitle")}>
      <Field
        label={t("settings.general.retention")}
        hint={t("settings.general.retentionHint")}
        error={errorText("retentionDays")}
        status={<SavePill state={fieldState("retentionDays")} onRetry={retry} />}
      >
        {(control) => (
          <div className="flex items-center gap-3">
            <div className="w-32">
              <Input
                {...control}
                type="number"
                inputMode="numeric"
                min={MIN_RETENTION_DAYS}
                max={MAX_RETENTION_DAYS}
                step={1}
                value={draft ?? form.retentionDays}
                disabled={disabled}
                onChange={(event) => setDraft(event.target.value)}
                onBlur={commit}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    commit();
                  }
                }}
              />
            </div>
            <span className="text-sm text-ink-muted">{t("settings.general.retentionUnit")}</span>
          </div>
        )}
      </Field>
    </Card>
  );
}
