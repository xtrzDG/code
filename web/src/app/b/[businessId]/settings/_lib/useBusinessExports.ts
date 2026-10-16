"use client";

import { useEffect, useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import {
  BUSINESS_EXPORT_POLL_MS,
  hasWorkingExport,
  linkHref,
  withDownloadCounted,
  withExport,
  type BusinessExport,
} from "./businessExports";

/** Let the browser fetch a file to disk (streamed, not kept in memory), named by the API. */
function startDownload(href: string): void {
  const link = document.createElement("a");
  link.href = href;
  link.download = "";
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  link.remove();
}

/**
 * The business's latest full exports, polled while one waits or is being
 * built; starting a new one (the API answers with the export already on its
 * way, if any); and downloading one through a one-time link that works for
 * a few minutes, only in this owner's session. Each asks an owner who
 * signed in long ago to confirm it is them first.
 */
export function useBusinessExports({ enabled }: { enabled: boolean }) {
  const { t, locale } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const businessId = business.id;
  const [downloading, setDownloading] = useState<string | null>(null);
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
  const link = useMutation(
    (exportId: string) =>
      api.POST("/v1/businesses/{business_id}/business-exports/{export_id}/download-link", {
        params: { path: { business_id: businessId, export_id: exportId } },
      }),
    { errorMessages: { conflict: "dataExports.full.usedUp", not_found: "dataExports.full.gone" } },
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

  const download = async (item: BusinessExport) => {
    if (downloading !== null) {
      return;
    }
    setDownloading(item.id);
    try {
      const result = await link.run(item.id);
      if (!result.ok) {
        // Used up or gone meanwhile: show the export as it is now.
        reload();
        return;
      }
      const href = linkHref(result.data.download_path);
      if (href === null) {
        return;
      }
      startDownload(href);
      setData((current) => current && { items: withDownloadCounted(current.items, item.id) });
      toast.success(t("dataExports.full.downloadStarted"));
    } finally {
      setDownloading(null);
    }
  };

  return { exports, items, isWorking, begin, isStarting: start.isPending, download, downloading };
}
