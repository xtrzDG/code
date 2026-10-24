"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { unwrap } from "@/api/result";
import { useBusiness } from "@/components/business/BusinessContext";
import { useToast } from "@/components/ui";
import { isoDay } from "@/components/workspace/helpers";
import { useI18n } from "@/i18n/client";

import { definedQuery, fallbackCsvName, fileNameFromDisposition, saveFile, type CsvQuery, type CsvTable } from "./csvExport";

/**
 * Downloading a table as CSV with the list's filters, headings in the
 * cabinet's language. The API asks an owner who signed in long ago to
 * confirm it is them first (the step-up dialog, then the request runs
 * again); the file is saved under the name the API gave.
 */
export function useCsvExport() {
  const { t, locale } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const [exporting, setExporting] = useState<CsvTable | null>(null);

  const download = async (table: CsvTable, query: CsvQuery = {}): Promise<boolean> => {
    setExporting(table);
    try {
      const result = await api.GET("/v1/businesses/{business_id}/exports/{table}", {
        params: {
          path: { business_id: business.id, table },
          query: { ...definedQuery(query), language: locale },
        },
        headers: { Accept: "text/csv" },
        parseAs: "blob",
      });
      const blob = await unwrap(Promise.resolve(result));
      saveFile(
        blob,
        fileNameFromDisposition(result.response.headers.get("content-disposition"), fallbackCsvName(table, isoDay(new Date()))),
      );
      toast.success(t("dataExports.csv.saved"));
      return true;
    } catch (error) {
      toast.error(error);
      return false;
    } finally {
      setExporting(null);
    }
  };

  return { exporting, download };
}
