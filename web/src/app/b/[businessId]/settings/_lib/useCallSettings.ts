"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";

import { TEXT_BACK_LIST_SIZE, type CallSettingsBody } from "./calls";

/**
 * Settings → Calls of the current business (owners): the settings with
 * the template texts, the latest text-backs (a view the API audits), and
 * saving the settings.
 */
export function useCallSettings() {
  const { business } = useBusiness();
  const path = { business_id: business.id };
  const settingsKey = queryKeys.calls.settings(business.id);
  const settings = useQuery(settingsKey, () =>
    api.GET("/v1/businesses/{business_id}/call-settings", { params: { path } }),
  );
  const textBacks = useQuery(queryKeys.calls.textBacks(business.id), () =>
    api.GET("/v1/businesses/{business_id}/text-backs", {
      params: { path, query: { limit: String(TEXT_BACK_LIST_SIZE) } },
    }),
  );
  const save = useMutation(
    (body: CallSettingsBody) => api.PUT("/v1/businesses/{business_id}/call-settings", { params: { path }, body }),
    { errorToast: false },
  );
  return { settings, textBacks, save };
}

export type CallSettingsState = ReturnType<typeof useCallSettings>;
