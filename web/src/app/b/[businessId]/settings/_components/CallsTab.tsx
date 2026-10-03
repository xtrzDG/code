"use client";

import { ErrorState, LoadingRegion, SkeletonCard } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { useCallSettings } from "../_lib/useCallSettings";
import { CallSettingsFormCard } from "./calls/CallSettingsFormCard";
import { TemplateTextCard } from "./calls/TemplateTextCard";
import { TextBackHistoryCard } from "./calls/TextBackHistoryCard";

/**
 * Settings → Calls (owners): a summary to staff after every call, a
 * message to callers who did not get through (the WhatsApp template, else
 * an SMS), the template text to register with Meta in each language, and
 * the latest callers who did not get through with what they were sent.
 */
export function CallsTab() {
  const { t } = useI18n();
  const state = useCallSettings();
  const { settings } = state;

  if (settings.error && !settings.data) {
    return <ErrorState error={settings.error} onRetry={settings.reload} className="py-6" />;
  }

  if (!settings.data) {
    return (
      <LoadingRegion label={t("common.loading")} className="space-y-6">
        <SkeletonCard lines={3} />
        <SkeletonCard lines={6} />
      </LoadingRegion>
    );
  }

  return (
    <div className="space-y-6">
      <CallSettingsFormCard stored={settings.data} state={state} />
      <TemplateTextCard previews={settings.data.template_previews ?? []} />
      <TextBackHistoryCard textBacks={state.textBacks} />
    </div>
  );
}
