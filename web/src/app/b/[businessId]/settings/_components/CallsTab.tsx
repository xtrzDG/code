"use client";

import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { ErrorState, LoadingRegion, PhoneFold, PhoneFolds, SkeletonCard } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { useCallSettings } from "../_lib/useCallSettings";
import { CallSettingsFormCard } from "./calls/CallSettingsFormCard";
import { TemplateTextCard } from "./calls/TemplateTextCard";
import { TextBackHistoryCard } from "./calls/TextBackHistoryCard";

/** The folded rows a person opened on a phone, remembered for them (lib/userPreference.ts). */
const OPEN_FOLDS_PREFERENCE = "settings-calls-open";

/**
 * Settings → Calls (owners): a summary to staff after every call, a
 * message to callers who did not get through (the WhatsApp template, else
 * an SMS), the recording of calls and transfers to staff, the template
 * text to register with Meta in each language, and the latest callers who
 * did not get through with what they were sent.
 *
 * On a phone the switches stay in reach: the recording (its state in the
 * row), the template texts (how many languages) and the latest text-backs
 * (how many) fold into rows that open on a tap (PhoneFold). Large screens
 * show every card.
 */
export function CallsTab() {
  const { t, tp } = useI18n();
  const { me } = useBusiness();
  const format = useBusinessFormat();
  const state = useCallSettings();
  const { settings, textBacks } = state;

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

  const previews = settings.data.template_previews ?? [];
  const history = textBacks.data?.items;
  return (
    <PhoneFolds preference={OPEN_FOLDS_PREFERENCE} userId={me.user.id}>
      {/* A flex column: the folds' wrappers take no box on large screens, so the gaps sit between the cards. */}
      <div className="flex flex-col gap-6">
        <CallSettingsFormCard stored={settings.data} state={state} />
        <PhoneFold name="template" title={t("callSettings.template.title")} summary={tp("callSettings.template.languages", previews.length)}>
          <TemplateTextCard previews={previews} />
        </PhoneFold>
        <PhoneFold
          name="history"
          title={t("callSettings.history.title")}
          summary={history ? format.number(history.length) : null}
        >
          <TextBackHistoryCard textBacks={textBacks} />
        </PhoneFold>
      </div>
    </PhoneFolds>
  );
}
