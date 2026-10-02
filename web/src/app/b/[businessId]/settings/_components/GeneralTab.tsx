"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { useApiQuery } from "@/api/hooks";
import { useBusiness } from "@/components/business/BusinessContext";
import { ErrorState, LoadingBlock } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import type { BusinessView } from "../_lib/general";
import { AssistantStatusCard } from "./general/AssistantStatusCard";
import { GeneralSettingsForm } from "./general/GeneralSettingsForm";

/**
 * Business details, languages and time, recording retention; and the
 * assistant's live/paused switch. The form starts from the business as
 * stored when the tab opens (the layout's copy may be older), and saves
 * carry the business revision they were made from. A save refused because
 * someone saved since is put on top of what is stored now: when nobody
 * else changed the same fields, it is saved again at once; otherwise those
 * fields show the stored values, the rest keeps what was typed, and the
 * form says so.
 */
export function GeneralTab() {
  const { t } = useI18n();
  const { business } = useBusiness();
  // The layout loads the business once and keeps it across pages, so a save
  // made since (platform bot, billing, another owner) leaves its revision
  // behind: start from the business as stored now, else the first save is
  // refused as stale.
  const stored = useApiQuery(
    () => api.GET("/v1/businesses/{business_id}", { params: { path: { business_id: business.id } } }),
    [business.id],
  );
  // The business as the status switch last saved it: the form takes over
  // its revision, so its next save is not refused for this tab's own change.
  const [switched, setSwitched] = useState<BusinessView | null>(null);
  return (
    <div className="space-y-6">
      <AssistantStatusCard onSaved={setSwitched} />
      {stored.data ? (
        <GeneralSettingsForm key={business.id} initial={stored.data} switched={switched} />
      ) : stored.error ? (
        <ErrorState error={stored.error} onRetry={stored.reload} className="py-6" />
      ) : (
        <LoadingBlock label={t("common.loading")} className="min-h-48" />
      )}
    </div>
  );
}
