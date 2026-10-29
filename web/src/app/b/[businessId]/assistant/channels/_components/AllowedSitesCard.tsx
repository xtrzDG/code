"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { Schema } from "@/api/types";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { Badge, Card, ErrorState, LoadingRegion, SkeletonText } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { AllowedSitesEditor } from "./AllowedSitesEditor";

type AllowedSitesView = Schema<"WidgetAllowedOriginsView">;

/**
 * The websites allowed to show the website chat
 * (GET·PUT …/channels/web/allowed-origins). Team members see the list;
 * owners change it. An empty list lets any website show the chat; the
 * hosted chat page and this cabinet's preview always may.
 */
export function AllowedSitesCard({ canManage }: { canManage: boolean }) {
  const { t, tp } = useI18n();
  const { business } = useBusiness();
  const sites = useQuery(queryKeys.channels.allowedOrigins(business.id), () =>
    api.GET("/v1/businesses/{business_id}/channels/web/allowed-origins", {
      params: { path: { business_id: business.id } },
    }),
  );
  const view = sites.data;

  return (
    <Card
      aria-label={t("widgetSites.title")}
      title={t("widgetSites.title")}
      description={t("widgetSites.description")}
      actions={
        view ? (
          view.is_restricted ? (
            <Badge tone="info">{tp("widgetSites.sites", view.origins.length)}</Badge>
          ) : (
            <Badge tone="neutral">{t("widgetSites.anySite")}</Badge>
          )
        ) : undefined
      }
    >
      {sites.error && !view ? (
        <ErrorState error={sites.error} onRetry={sites.reload} />
      ) : !view ? (
        <LoadingRegion label={t("common.loading")}>
          <SkeletonText lines={3} />
        </LoadingRegion>
      ) : (
        // Remounted when the saved list changes, so the draft starts from it.
        <AllowedSitesEditor
          key={view.origins.join(" ")}
          saved={view.origins}
          canManage={canManage}
          onSaved={(next: AllowedSitesView) => sites.setData(next)}
        />
      )}
    </Card>
  );
}
