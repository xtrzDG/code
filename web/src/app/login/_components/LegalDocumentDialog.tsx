"use client";

import { api } from "@/api/client";
import { CATALOG_STALE_MS } from "@/api/catalog";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { Alert, Button, ErrorState, LoadingRegion, Modal, SkeletonText } from "@/components/ui";
import { MarkdownDocument } from "@/components/workspace/MarkdownDocument";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";
import { dateTimeFormat } from "@/lib/intl/formatters";

import type { LegalDocumentKind } from "../_lib/legalConsent";

/** A version's day ("2026-10-05") as text: "5 October 2026". */
function formatDay(day: string, locale: string): string {
  return dateTimeFormat(locale, { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" }).format(
    new Date(`${day}T00:00:00Z`),
  );
}

/**
 * The terms, the privacy policy or the cookie statement in a dialog over
 * the sign-in page, so reading them never loses the code step. The version
 * shown is the one the acceptance line names; the text itself names its
 * version and says when it is still a template, so the dialog adds only
 * a newer version already published and a fallback language.
 */
export function LegalDocumentDialog({
  document,
  version,
  onClose,
}: {
  document: LegalDocumentKind | null;
  version: string | null;
  onClose: () => void;
}) {
  const { t, locale } = useI18n();
  const kind = document ?? "terms";
  const text = useQuery(
    queryKeys.catalog.legal(kind, version ?? "", locale),
    () =>
      api.GET("/v1/legal/{document}", {
        params: { path: { document: kind }, query: { language: locale, ...(version ? { version } : {}) } },
      }),
    { enabled: document !== null, staleMs: CATALOG_STALE_MS },
  );
  const data = text.data;

  return (
    <Modal
      open={document !== null}
      onClose={onClose}
      size="xl"
      title={data?.title ?? t("legalConsent.loading")}
      footer={
        <div className="flex justify-end">
          <Button variant="secondary" onClick={onClose}>
            {t("common.close")}
          </Button>
        </div>
      }
    >
      {text.error && !data ? (
        <ErrorState error={text.error} onRetry={text.reload} className="py-6" />
      ) : !data ? (
        <LoadingRegion label={t("legalConsent.loading")} className="py-1">
          <SkeletonText lines={10} />
        </LoadingRegion>
      ) : (
        <div className="space-y-4">
          {data.language !== locale ? (
            <Alert tone="info">{t("legalConsent.otherLanguage", { language: languageName(data.language, locale) })}</Alert>
          ) : null}
          {data.upcoming_version ? (
            <Alert tone="info">
              {t("legalConsent.documentUpcoming", { date: formatDay(data.upcoming_version, locale) })}
            </Alert>
          ) : null}
          <MarkdownDocument source={data.text} lang={data.language} hideTitle />
        </div>
      )}
    </Modal>
  );
}
