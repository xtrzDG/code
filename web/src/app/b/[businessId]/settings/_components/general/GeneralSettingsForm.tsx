"use client";

import { AutosaveHint } from "@/components/forms/AutosaveHint";
import { useBusiness } from "@/components/business/BusinessContext";
import { ConfirmDialog } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import type { BusinessView } from "../../_lib/general";
import { useGeneralChoices } from "../../_lib/useGeneralChoices";
import { useGeneralSettings } from "../../_lib/useGeneralSettings";
import { BusinessDetailsCard } from "./BusinessDetailsCard";
import { LanguagesTimeCard } from "./LanguagesTimeCard";
import { RecordingsCard } from "./RecordingsCard";
import { StaleNotices } from "./StaleNotices";

/**
 * The General form: business details, languages and time, recording
 * retention. Every change saves itself (no Save button); keeping
 * recordings for less time deletes the older ones, so it asks first.
 */
export function GeneralSettingsForm({ initial, switched }: { initial: BusinessView; switched: BusinessView | null }) {
  const { t } = useI18n();
  const { isOwner } = useBusiness();
  const settings = useGeneralSettings(initial, switched);
  const options = useGeneralChoices(settings.baseline, settings.form);

  return (
    <div className="space-y-6">
      {isOwner ? (
        <div className="flex justify-end">
          <AutosaveHint state={settings.state} />
        </div>
      ) : null}
      <StaleNotices settings={settings} />
      <BusinessDetailsCard settings={settings} />
      <LanguagesTimeCard settings={settings} options={options} />
      <RecordingsCard settings={settings} />
      <ConfirmDialog
        open={settings.confirming}
        onClose={settings.cancelConfirmation}
        onConfirm={settings.confirm}
        title={t("settings.general.retentionShorterTitle")}
        description={t("settings.general.retentionShorterDescription", { days: settings.form.retentionDays.trim() })}
        confirmLabel={t("settings.general.retentionShorterConfirm")}
      />
    </div>
  );
}
