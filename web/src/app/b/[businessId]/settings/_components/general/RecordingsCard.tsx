"use client";

import { Card, Field, Input } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { MAX_RETENTION_DAYS, MIN_RETENTION_DAYS } from "../../_lib/general";
import type { GeneralSettings } from "../../_lib/useGeneralSettings";

/** How long call recordings are kept. */
export function RecordingsCard({ settings }: { settings: GeneralSettings }) {
  const { t } = useI18n();
  const { form, disabled, update, errorText } = settings;
  return (
    <Card title={t("settings.general.recordingsTitle")}>
      <Field label={t("settings.general.retention")} hint={t("settings.general.retentionHint")} error={errorText("retentionDays")}>
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
                value={form.retentionDays}
                disabled={disabled}
                onChange={(event) => update("retentionDays", event.target.value)}
              />
            </div>
            <span className="text-sm text-ink-muted">{t("settings.general.retentionUnit")}</span>
          </div>
        )}
      </Field>
    </Card>
  );
}
