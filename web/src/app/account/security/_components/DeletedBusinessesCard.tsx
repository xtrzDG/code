"use client";

/**
 * Account → Security: the businesses this person owned that were closed
 * and deleted, each with why, when, and its deletion certificate (a PDF in
 * the reader's language, once the deletion is complete). Hidden while
 * there are none. Dates are UTC, as on the certificate.
 */

import { useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { ApiResult } from "@/api/result";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import type { BusinessDeletionView } from "@/api/types";
import { fileNameFromDisposition, saveFile } from "@/components/exports/csvExport";
import { IconDownload } from "@/components/icons";
import { Button, Card, UserContent } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { formatDate } from "@/lib/format";

interface Certificate {
  blob: Blob;
  fileName: string;
}

export function DeletedBusinessesCard() {
  const { t, locale } = useI18n();
  const [pending, setPending] = useState<string | null>(null);
  const deletions = useQuery(queryKeys.businessDeletions.list(), () => api.GET("/v1/me/business-deletions"));
  const download = useMutation(async (deletion: BusinessDeletionView): Promise<ApiResult<Certificate>> => {
    const result = await api.GET("/v1/me/business-deletions/{deletion_id}/certificate", {
      params: { path: { deletion_id: deletion.id }, query: { language: locale } },
      headers: { Accept: "application/pdf" },
      parseAs: "blob",
    });
    const fallback = `deletion-certificate-${deletion.id}.pdf`;
    return {
      data:
        result.data === undefined
          ? undefined
          : { blob: result.data, fileName: fileNameFromDisposition(result.response.headers.get("content-disposition"), fallback) },
      error: result.error,
      response: result.response,
    };
  });

  const items = deletions.data?.items ?? [];
  if (items.length === 0) {
    return null;
  }
  const date = (value: number) => formatDate(value, { locale, timeZone: "UTC" });

  const onDownload = async (deletion: BusinessDeletionView) => {
    if (pending !== null) {
      return;
    }
    setPending(deletion.id);
    try {
      const result = await download.run(deletion);
      if (result.ok) {
        saveFile(result.data.blob, result.data.fileName);
      }
    } finally {
      setPending(null);
    }
  };

  return (
    <Card title={t("closure.deletions.title")} description={t("closure.deletions.description")} padded={false} data-testid="deleted-businesses">
      <ul className="divide-y divide-line">
        {items.map((deletion) => (
          <li key={deletion.id} className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 px-5 py-4">
            <div className="min-w-0 flex-1 basis-56 text-sm">
              <p id={`deleted-${deletion.id}`} className="font-medium break-words text-ink">
                <UserContent>{deletion.business_name}</UserContent>
              </p>
              <p className="mt-0.5 text-ink-muted">
                {t(deletion.reason === "unpaid_subscription" ? "closure.deletions.reasonUnpaid" : "closure.deletions.reasonOwner")}
                <span className="text-ink-subtle"> · </span>
                {deletion.state === "completed" && deletion.completed_at != null
                  ? t("closure.deletions.completedOn", { date: date(deletion.completed_at) })
                  : t("closure.deletions.startedOn", { date: date(deletion.started_at) })}
              </p>
            </div>
            {deletion.state === "completed" ? (
              <Button
                variant="secondary"
                size="sm"
                isLoading={pending === deletion.id}
                loadingText={t("closure.deletions.downloading")}
                onClick={() => void onDownload(deletion)}
                // Named by its visible words (WCAG 2.5.3); the business's name describes it.
                aria-describedby={`deleted-${deletion.id}`}
              >
                <IconDownload className="size-4" aria-hidden />
                {t("closure.deletions.certificate")}
              </Button>
            ) : (
              <span className="text-sm text-ink-muted">{t("closure.deletions.inProgress")}</span>
            )}
          </li>
        ))}
      </ul>
    </Card>
  );
}
