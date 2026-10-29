"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { ApiResult } from "@/api/result";
import { useMutation } from "@/api/useMutation";
import { useBusiness } from "@/components/business/BusinessContext";
import { useI18n } from "@/i18n/client";

import type { InvoiceView } from "./billing";
import { fileNameFromDisposition, saveFile, type BillingDocumentKind } from "./billingDetails";

interface DownloadedFile {
  blob: Blob;
  fileName: string;
}

/**
 * Downloading an invoice or its receipt as a PDF in the reader's language.
 * The API writes an audit entry for each download and numbers an invoice
 * issued before numbering on its first one, so the list loads again then.
 * `pending` names the document being downloaded ("<invoice id>:<kind>").
 */
export function useBillingDocumentDownload() {
  const { business } = useBusiness();
  const { locale } = useI18n();
  const [pending, setPending] = useState<string | null>(null);
  const download = useMutation(
    async (invoice: InvoiceView, kind: BillingDocumentKind): Promise<ApiResult<DownloadedFile>> => {
      const result = await api.GET("/v1/businesses/{business_id}/billing/invoices/{invoice_id}/documents/{document_kind}", {
        params: {
          path: { business_id: business.id, invoice_id: invoice.id, document_kind: kind },
          query: { language: locale },
        },
        headers: { Accept: "application/pdf" },
        parseAs: "blob",
      });
      const fallback = `${kind}-${invoice.number ?? invoice.id}.pdf`;
      return {
        data:
          result.data === undefined
            ? undefined
            : { blob: result.data, fileName: fileNameFromDisposition(result.response.headers.get("content-disposition"), fallback) },
        error: result.error,
        response: result.response,
      };
    },
    {
      invalidate: (_file, invoice) => (invoice.number ? [] : [queryKeys.billing.overview(business.id, locale)]),
      errorMessages: { conflict: "billing.documents.unavailable" },
    },
  );

  const run = async (invoice: InvoiceView, kind: BillingDocumentKind): Promise<void> => {
    if (pending !== null) {
      return;
    }
    setPending(`${invoice.id}:${kind}`);
    try {
      const result = await download.run(invoice, kind);
      if (result.ok) {
        saveFile(result.data.blob, result.data.fileName);
      }
    } finally {
      setPending(null);
    }
  };

  return { run, pending };
}
