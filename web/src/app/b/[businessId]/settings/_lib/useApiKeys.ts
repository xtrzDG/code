"use client";

/**
 * Settings → Integrations → API keys (owners): the keys (never their
 * secrets), creating one (its token comes back once) and revoking one.
 */

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import type { ApiKeyBody, ApiKeyList, ApiKeyView } from "@/lib/apiIntegrations";

export const API_KEY_REASONS = {
  api_key_limit_reached: (reason: { details: readonly string[] }) => ({
    key: "apiIntegrations.apiKeys.reasons.api_key_limit_reached" as const,
    values: { count: Number(reason.details[0] ?? 0) },
  }),
};

export function useApiKeys() {
  const { business } = useBusiness();
  const path = { business_id: business.id };
  const listKey = queryKeys.integrations.apiKeys(business.id);
  const list = useQuery(listKey, () => api.GET("/v1/businesses/{business_id}/api-keys", { params: { path } }));

  const create = useMutation(
    (body: ApiKeyBody) => api.POST("/v1/businesses/{business_id}/api-keys", { params: { path }, body }),
    { errorToast: false },
  );
  const revoke = useMutation(
    (apiKey: ApiKeyView) =>
      api.DELETE("/v1/businesses/{business_id}/api-keys/{api_key_id}", {
        params: { path: { ...path, api_key_id: apiKey.id } },
      }),
    {
      // Its webhooks are gone too.
      invalidate: [listKey, queryKeys.integrations.webhooks(business.id)],
    },
  );

  return {
    list,
    async createKey(body: ApiKeyBody) {
      const result = await create.run(body);
      if (result.ok) {
        const created = result.data.api_key;
        queryCache.update<ApiKeyList>(listKey, (data) => ({ ...data, items: [created, ...(data.items ?? [])] }));
      }
      return result;
    },
    revokeKey: revoke.run,
    isCreating: create.isPending,
    isRevoking: revoke.isPending,
  };
}
