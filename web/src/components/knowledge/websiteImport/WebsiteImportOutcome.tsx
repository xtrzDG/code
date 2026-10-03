"use client";

import type { Schema } from "@/api/types";
import { IconCheck, IconGlobe, IconRefresh } from "@/components/icons";
import { Button, EmptyState } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { siteHost, type WebsiteImport } from "@/lib/knowledge/websiteImport";

/**
 * A finished import: the drafts it found wait for the review drawer, or
 * nothing readable was found. Nothing is added to the knowledge base here.
 */
export function WebsiteImportOutcome({
  view,
  justFinished,
  onReview,
  onAnother,
}: {
  view: WebsiteImport;
  /** The import finished while the owner watched it (rather than earlier). */
  justFinished: boolean;
  onReview: (result: Schema<"MenuImportResult">) => void;
  onAnother: () => void;
}) {
  const { t, tp } = useI18n();
  const result = view.result;
  const waiting = result?.items?.length ?? 0;
  const another = (
    <Button variant="secondary" leadingIcon={<IconRefresh className="size-4" aria-hidden />} onClick={onAnother}>
      {t("knowledge.website.another")}
    </Button>
  );

  if (!result || waiting === 0) {
    return (
      <EmptyState
        className="py-8"
        icon={<IconGlobe className="size-6" />}
        title={t("knowledge.website.nothingTitle")}
        description={t("knowledge.website.nothingDescription")}
        action={another}
      />
    );
  }

  return (
    <div className="flex flex-col items-center py-6 text-center" data-testid="website-import-outcome">
      <div
        aria-hidden
        className="mb-4 flex size-12 items-center justify-center rounded-2xl bg-success-soft text-success ring-1 ring-success/25 motion-safe:animate-settle"
      >
        <IconCheck className="size-6" />
      </div>
      <h3 className="text-base font-semibold text-ink" role={justFinished ? "status" : undefined}>
        {justFinished ? tp("knowledge.website.doneTitle", waiting) : t("knowledge.website.waitingTitle")}
      </h3>
      <p className="mt-1.5 max-w-md text-sm text-ink-muted">
        {justFinished
          ? tp("knowledge.website.doneDescription", view.pages_read)
          : tp("knowledge.website.waitingDescription", waiting, { host: siteHost(view.url) })}
      </p>
      <div className="mt-6 flex flex-wrap justify-center gap-2">
        <Button onClick={() => onReview(result)}>{t("knowledge.website.review")}</Button>
        {another}
      </div>
    </div>
  );
}
