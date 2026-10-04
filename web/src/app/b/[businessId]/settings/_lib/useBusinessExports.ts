"use client";

import { useEffect } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { BUSINESS_EXPORT_POLL_MS, hasWorkingExport, withExport, type BusinessExport } from "./businessExports";

/**
 * The business's latest full exports, polled while one waits or is being
 * built, and starting a new one (the API answers with the export already
 * on its way, if any). Both ask an owner who signed in long ago to confirm
 * it is them first.
 */
export function useBusinessExports({ enabled }: { enabled: boolean }) {
  const { t, locale } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const businessId = business.id;
  const exports = useQuery(
    queryKeys.settings.businessExports(businessId),
    () => api.GET("/v1/businesses/{business_id}/business-exports", { params: { path: { business_id: businessId } } }),
    { enabled, staleMs: 0 },
  );
  const start = useMutation(() =>
    api.POST("/v1/businesses/{business_id}/business-exports", {
      params: { path: { business_id: businessId } },
      body: { language: locale },
    }),
  );
  const items: BusinessExport[] | undefined = exports.data?.items;
  const isWorking = hasWorkingExport(items);
  const { reload, setData } = exports;

  useEffect(() => {
    if (!isWorking) {
      return;
    }
    const timer = window.setInterval(reload, BUSINESS_EXPORT_POLL_MS);
    return () => window.clearInterval(timer);
  }, [isWorking, reload]);

  const begin = async () => {
    const result = await start.run();
    if (result.ok) {
      setData((current) => ({ items: withExport(current?.items, result.data) }));
      toast.success(t("dataExports.full.started"));
    }
  };

  return { exports, items, isWorking, begin, isStarting: start.isPending };
}
