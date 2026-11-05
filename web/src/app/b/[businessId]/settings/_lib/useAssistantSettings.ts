"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";

import type { AssistantSettingsBody } from "./customerMemory";

/** Settings → General's customer memory of the current business: read by the team, saved by owners. */
export function useAssistantSettings() {
  const { business } = useBusiness();
  const path = { business_id: business.id };
  const settings = useQuery(queryKeys.assistantSettings.detail(business.id), () =>
    api.GET("/v1/businesses/{business_id}/assistant-settings", { params: { path } }),
  );
  const save = useMutation((body: AssistantSettingsBody) =>
    api.PUT("/v1/businesses/{business_id}/assistant-settings", { params: { path }, body }),
  );
  return { settings, save };
}
