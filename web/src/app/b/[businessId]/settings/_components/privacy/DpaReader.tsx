"use client";

import { api } from "@/api/client";
import { useApiQuery } from "@/api/hooks";
import { Alert, Button, ErrorState, LoadingBlock, Modal } from "@/components/ui";
import { MarkdownDocument } from "@/components/workspace/MarkdownDocument";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";

/** The agreement text in a dialog, in the interface language when it exists. */
export function DpaReader({
  open,
  version,
  canConfirm,
  onClose,
  onConfirm,
}: {
  open: boolean;
  version: string;
  canConfirm: boolean;
  onClose: () => void;
  onConfirm: () => void;
}) {
  const { t, locale } = useI18n();
  const document = useApiQuery(
    () => api.GET("/v1/legal/dpa/{version}", { params: { path: { version }, query: { language: locale } } }),
    [version, locale],
    { enabled: open && version !== "" },
  );
  const data = document.data;

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="xl"
      title={data?.title ?? t("settings.dpa.title")}
      footer={
        <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
          <Button variant="secondary" onClick={onClose}>
            {t("common.close")}
          </Button>
          {canConfirm && data ? <Button onClick={onConfirm}>{t("settings.dpaReader.confirmRead")}</Button> : null}
        </div>
      }
    >
      {document.error && !data ? (
        <ErrorState error={document.error} onRetry={document.reload} className="py-6" />
      ) : !data ? (
        <LoadingBlock label={t("common.loading")} className="min-h-48" />
      ) : (
        <div className="space-y-4">
          {data.language !== locale ? (
            <Alert tone="info">{t("settings.dpaReader.otherLanguage", { language: languageName(data.language, locale) })}</Alert>
          ) : null}
          <MarkdownDocument source={data.text} lang={data.language} hideTitle />
        </div>
      )}
    </Modal>
  );
}
