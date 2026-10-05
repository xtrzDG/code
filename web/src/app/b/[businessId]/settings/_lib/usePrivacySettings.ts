"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";

import type { PrivacySettingsBody } from "./privacySettings";

/**
 * Settings → Privacy → "How long data is kept" (owners): the retention
 * periods with the latest cleanup, and saving the periods (a shorter one
 * asks an owner who signed in long ago to confirm it is them first).
 */
export function usePrivacySettings({ enabled }: { enabled: boolean }) {
  const { business } = useBusiness();
  const path = { business_id: business.id };
  const settings = useQuery(
    queryKeys.settings.privacy(business.id),
    () => api.GET("/v1/businesses/{business_id}/privacy-settings", { params: { path } }),
    { enabled },
  );
  const save = useMutation(
    (body: PrivacySettingsBody) => api.PUT("/v1/businesses/{business_id}/privacy-settings", { params: { path }, body }),
    { errorToast: false },
  );
  return { settings, save };
}

export type PrivacySettingsState = ReturnType<typeof usePrivacySettings>;
