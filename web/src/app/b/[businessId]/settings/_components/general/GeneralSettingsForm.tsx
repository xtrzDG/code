"use client";

import { useBusiness } from "@/components/business/BusinessContext";

import type { BusinessView } from "../../_lib/general";
import { useGeneralChoices } from "../../_lib/useGeneralChoices";
import { useGeneralSettings } from "../../_lib/useGeneralSettings";
import { BusinessDetailsCard } from "./BusinessDetailsCard";
import { GeneralSaveBar } from "./GeneralSaveBar";
import { LanguagesTimeCard } from "./LanguagesTimeCard";
import { RecordingsCard } from "./RecordingsCard";
import { StaleNotices } from "./StaleNotices";

/** The General form: business details, languages and time, recording retention. */
export function GeneralSettingsForm({ initial, switched }: { initial: BusinessView; switched: BusinessView | null }) {
  const { isOwner } = useBusiness();
  const settings = useGeneralSettings(initial, switched);
  const options = useGeneralChoices(settings.baseline, settings.form);

  return (
    <form onSubmit={settings.onSubmit} noValidate className="space-y-6">
      <StaleNotices settings={settings} />
      <BusinessDetailsCard settings={settings} />
      <LanguagesTimeCard settings={settings} options={options} />
      <RecordingsCard settings={settings} />
      {isOwner ? <GeneralSaveBar settings={settings} /> : null}
    </form>
  );
}
