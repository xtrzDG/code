"use client";

import { Alert } from "@/components/ui";
import { useI18n } from "@/i18n/client";

/**
 * A list's note while a data task after a deploy still fills what it pages
 * by (`is_indexing` of the page): older rows may be missing for a while.
 */
export function StillIndexingNote({ isIndexing }: { isIndexing: boolean | undefined }) {
  const { t } = useI18n();
  if (!isIndexing) {
    return null;
  }
  return (
    <div role="status">
      <Alert tone="info" title={t("dataTasks.indexing.title")}>
        {t("dataTasks.indexing.body")}
      </Alert>
    </div>
  );
}
