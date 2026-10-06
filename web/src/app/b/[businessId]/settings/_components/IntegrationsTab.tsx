"use client";

import { api } from "@/api/client";
import { useIntegrations } from "@/api/integrations";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { ErrorState, LoadingRegion, SkeletonCard } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { IntegrationsCard } from "./integrations/IntegrationsCard";
import { ResourceCalendarsCard } from "./integrations/ResourceCalendarsCard";

/**
 * Settings → Integrations (owners): Google Calendar, imported and shared
 * iCal calendars and Cal.com, each with its state, how many resources use
 * it and when it last read; then the resources that have calendars. The
 * calendars themselves are set per resource on Resources and hours.
 */
export function IntegrationsTab() {
  const { t } = useI18n();
  const { business } = useBusiness();
  const integrations = useIntegrations(business.id);
  const resources = useQuery(queryKeys.resources.list(business.id), () =>
    api.GET("/v1/businesses/{business_id}/resources", { params: { path: { business_id: business.id } } }),
  );

  if (integrations.error && !integrations.data) {
    return <ErrorState error={integrations.error} onRetry={integrations.reload} className="py-6" />;
  }

  if (!integrations.data) {
    return (
      <LoadingRegion label={t("common.loading")} className="space-y-6">
        <SkeletonCard lines={6} />
        <SkeletonCard lines={3} />
      </LoadingRegion>
    );
  }

  const names = new Map((resources.data?.items ?? []).map((resource) => [resource.id, resource.name]));
  // undefined while the names load, null for a resource that is gone.
  const resourceName = (resourceId: string) => (resources.data ? (names.get(resourceId) ?? null) : undefined);

  return (
    <div className="space-y-6">
      <IntegrationsCard items={integrations.data.items} />
      <ResourceCalendarsCard summaries={integrations.data.resources ?? []} resourceName={resourceName} />
    </div>
  );
}
