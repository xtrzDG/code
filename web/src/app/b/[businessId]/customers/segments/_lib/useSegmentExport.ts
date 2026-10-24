"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { unwrap } from "@/api/result";
import { useBusiness } from "@/components/business/BusinessContext";
import { fileNameFromDisposition, saveFile } from "@/components/exports/csvExport";
import { useToast } from "@/components/ui";
import { isoDay, safeFileName } from "@/components/workspace/helpers";
import { useI18n } from "@/i18n/client";

import type { Segment } from "./segmentRules";

/**
 * Downloading a segment's customers as CSV, headings in the cabinet's
 * language. An owner who signed in long ago confirms it is them first
 * (the step-up dialog, then the request runs again); the API audits it.
 */
export function useSegmentExport() {
  const { t, locale } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const [exporting, setExporting] = useState<string | null>(null);

  const download = async (segment: Segment): Promise<void> => {
    setExporting(segment.id);
    try {
      const result = await api.GET("/v1/businesses/{business_id}/customer-segments/{segment_id}/export", {
        params: { path: { business_id: business.id, segment_id: segment.id }, query: { language: locale } },
        headers: { Accept: "text/csv" },
        parseAs: "blob",
      });
      const blob = await unwrap(Promise.resolve(result));
      const fallback = `${safeFileName(segment.name) || "segment"}-${isoDay(new Date())}.csv`;
      saveFile(blob, fileNameFromDisposition(result.response.headers.get("content-disposition"), fallback));
      toast.success(t("dataExports.csv.saved"));
    } catch (error) {
      toast.error(error);
    } finally {
      setExporting(null);
    }
  };

  return { exporting, download };
}
