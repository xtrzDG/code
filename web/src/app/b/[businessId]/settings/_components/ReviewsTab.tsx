"use client";

import { ErrorState, LoadingRegion, SkeletonCard } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { useReviewSettings } from "../_lib/useReviewSettings";
import { FeedbackRequestsCard } from "./reviews/FeedbackRequestsCard";
import { ReviewSettingsFormCard } from "./reviews/ReviewSettingsFormCard";
import { ReviewStatsCard } from "./reviews/ReviewStatsCard";
import { ReviewTemplateCard } from "./reviews/ReviewTemplateCard";

/**
 * Settings → Reviews (owners): the last 30 days in numbers, feedback after
 * visits (when to ask, the WhatsApp template), the Google review link every
 * customer who answers gets, the template text to register with Meta, and
 * the latest visits asked about with the customers' answers.
 */
export function ReviewsTab() {
  const { t } = useI18n();
  const state = useReviewSettings();
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
      <ReviewStatsCard stats={state.stats} isLinkTracked={settings.data.is_link_tracked} />
      <ReviewSettingsFormCard stored={settings.data} state={state} />
      <ReviewTemplateCard previews={settings.data.template_previews ?? []} />
      <FeedbackRequestsCard requests={state.requests} />
    </div>
  );
}
