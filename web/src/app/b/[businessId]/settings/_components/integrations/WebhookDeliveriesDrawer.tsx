"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useCursorPage } from "@/api/useCursorPage";
import { useBusiness } from "@/components/business/BusinessContext";
import { Button, Drawer, EmptyState, ErrorState, InlineError, SkeletonText } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { WebhookDeliveryView, WebhookEndpointView } from "@/lib/apiIntegrations";

import { WebhookDeliveryRow } from "./WebhookDeliveryRow";

type DeliveryPage = { items?: WebhookDeliveryView[]; next_cursor?: string | null };

function DeliveryLog({ endpoint }: { endpoint: WebhookEndpointView }) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const log = useCursorPage<WebhookDeliveryView, DeliveryPage>(
    queryKeys.integrations.deliveries(business.id, endpoint.id),
    ({ cursor, limit }) =>
      api.GET("/v1/businesses/{business_id}/webhooks/{webhook_id}/deliveries", {
        params: {
          path: { business_id: business.id, webhook_id: endpoint.id },
          query: { limit: String(limit), ...(cursor ? { cursor } : {}) },
        },
      }),
    { pageSize: 20, staleMs: 0 },
  );

  if (log.error && !log.items) {
    return <ErrorState error={log.error} onRetry={log.reload} className="py-6" />;
  }
  if (!log.items) {
    return <SkeletonText lines={4} />;
  }
  if (log.items.length === 0) {
    return <EmptyState title={t("apiIntegrations.deliveries.empty")} className="py-8" />;
  }
  const replace = (updated: WebhookDeliveryView) =>
    log.updateItems((items) => items.map((item) => (item.id === updated.id ? updated : item)));
  return (
    <div className="space-y-3">
      <ul className="divide-y divide-line">
        {log.items.map((delivery) => (
          <WebhookDeliveryRow key={delivery.id} delivery={delivery} onRetried={replace} />
        ))}
      </ul>
      {log.moreError ? <InlineError error={log.moreError} /> : null}
      {log.hasMore ? (
        <Button variant="secondary" size="sm" isLoading={log.isLoadingMore} onClick={log.loadMore}>
          {t("apiIntegrations.deliveries.more")}
        </Button>
      ) : null}
    </div>
  );
}

/** The delivery log of one webhook, newest first, 30 days back. */
export function WebhookDeliveriesDrawer({ endpoint, onClose }: { endpoint: WebhookEndpointView | null; onClose: () => void }) {
  const { t } = useI18n();
  return (
    <Drawer
      open={endpoint !== null}
      onClose={onClose}
      title={t("apiIntegrations.deliveries.title")}
      description={endpoint ? t("apiIntegrations.deliveries.description", { url: endpoint.url }) : undefined}
      footer={
        <Button variant="secondary" onClick={onClose}>
          {t("apiIntegrations.deliveries.close")}
        </Button>
      }
    >
      {endpoint ? <DeliveryLog key={endpoint.id} endpoint={endpoint} /> : null}
    </Drawer>
  );
}
