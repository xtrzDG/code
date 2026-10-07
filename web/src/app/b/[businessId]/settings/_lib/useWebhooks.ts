"use client";

/**
 * Settings → Integrations → Webhooks (owners): the endpoints with the
 * event catalog, and every change of one. The list is replaced from each
 * answer, so a change shows at once without loading the list again.
 */

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import type {
  WebhookEndpointBody,
  WebhookEndpointChange,
  WebhookEndpointList,
  WebhookEndpointView,
} from "@/lib/apiIntegrations";

export const WEBHOOK_REASONS = {
  not_public: () => ({ key: "apiIntegrations.webhooks.reasons.not_public" as const }),
  webhook_limit_reached: (reason: { details: readonly string[] }) => ({
    pluralKey: "apiIntegrations.webhooks.reasons.webhook_limit_reached" as const,
    count: Number(reason.details[0] ?? 0),
  }),
};

export function useWebhooks() {
  const { business } = useBusiness();
  const path = { business_id: business.id };
  const listKey = queryKeys.integrations.webhooks(business.id);
  const list = useQuery(listKey, () => api.GET("/v1/businesses/{business_id}/webhooks", { params: { path } }));

  const replace = (endpoint: WebhookEndpointView) =>
    queryCache.update<WebhookEndpointList>(listKey, (data) => {
      const items = data.items ?? [];
      const known = items.some((item) => item.id === endpoint.id);
      return { ...data, items: known ? items.map((item) => (item.id === endpoint.id ? endpoint : item)) : [endpoint, ...items] };
    });
  const endpointPath = (endpoint: WebhookEndpointView) => ({ path: { ...path, webhook_id: endpoint.id } });

  const create = useMutation(
    (body: WebhookEndpointBody) => api.POST("/v1/businesses/{business_id}/webhooks", { params: { path }, body }),
    { errorToast: false },
  );
  const update = useMutation(
    (endpoint: WebhookEndpointView, change: WebhookEndpointChange) =>
      api.PATCH("/v1/businesses/{business_id}/webhooks/{webhook_id}", { params: endpointPath(endpoint), body: change }),
    { errorToast: false },
  );
  const rotate = useMutation((endpoint: WebhookEndpointView) =>
    api.POST("/v1/businesses/{business_id}/webhooks/{webhook_id}/rotate-secret", { params: endpointPath(endpoint) }),
  );
  const sendTest = useMutation(
    (endpoint: WebhookEndpointView) =>
      api.POST("/v1/businesses/{business_id}/webhooks/{webhook_id}/test", { params: endpointPath(endpoint) }),
    { invalidate: (_data, endpoint) => [queryKeys.integrations.deliveries(business.id, endpoint.id)] },
  );
  const remove = useMutation(
    (endpoint: WebhookEndpointView) =>
      api.DELETE("/v1/businesses/{business_id}/webhooks/{webhook_id}", { params: endpointPath(endpoint) }),
    {
      optimistic: (endpoint) =>
        queryCache.update<WebhookEndpointList>(listKey, (data) => ({
          ...data,
          items: (data.items ?? []).filter((item) => item.id !== endpoint.id),
        })),
    },
  );

  return {
    list,
    async createEndpoint(body: WebhookEndpointBody) {
      const result = await create.run(body);
      if (result.ok) replace(result.data.endpoint);
      return result;
    },
    async updateEndpoint(endpoint: WebhookEndpointView, change: WebhookEndpointChange) {
      const result = await update.run(endpoint, change);
      if (result.ok) replace(result.data);
      return result;
    },
    async rotateSecret(endpoint: WebhookEndpointView) {
      const result = await rotate.run(endpoint);
      if (result.ok) replace(result.data.endpoint);
      return result;
    },
    async sendTestEvent(endpoint: WebhookEndpointView) {
      const result = await sendTest.run(endpoint);
      // The attempt changed the endpoint's last attempt and success.
      list.reload();
      return result;
    },
    deleteEndpoint: remove.run,
    isSaving: create.isPending || update.isPending,
    isRotating: rotate.isPending,
    isDeleting: remove.isPending,
  };
}
