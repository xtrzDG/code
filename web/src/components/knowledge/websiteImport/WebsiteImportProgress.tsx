"use client";

import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import {
  currentPage,
  importPercent,
  importStage,
  siteHost,
  type WebsiteImport,
} from "@/lib/knowledge/websiteImport";

/** Three pages in perspective, the top one scanned while the site is read. */
function PageStack({ isReading }: { isReading: boolean }) {
  return (
    <div aria-hidden className="relative size-14 shrink-0 [perspective:240px]">
      <div className="absolute inset-0 [transform-style:preserve-3d] [transform:rotateX(18deg)_rotateY(-24deg)]">
        <div className="absolute inset-x-2 inset-y-1 translate-x-2 -translate-y-1 rounded-md border border-line bg-surface-muted [transform:translateZ(-14px)]" />
        <div className="absolute inset-x-2 inset-y-1 translate-x-1 rounded-md border border-line bg-surface [transform:translateZ(-7px)]" />
        <div className="absolute inset-x-2 inset-y-1 overflow-hidden rounded-md border border-accent/40 bg-surface shadow-md">
          <div className="mx-1.5 mt-2 h-1 rounded bg-line-strong/60" />
          <div className="mx-1.5 mt-1 h-1 w-2/3 rounded bg-line-strong/40" />
          <div className="mx-1.5 mt-1 h-1 w-1/2 rounded bg-line-strong/40" />
          {isReading ? (
            <div className="absolute inset-x-0 top-0 h-3 bg-gradient-to-b from-transparent via-accent/40 to-transparent motion-safe:animate-page-scan" />
          ) : null}
        </div>
      </div>
    </div>
  );
}

/** How far the reading of the business's website got, live. */
export function WebsiteImportProgress({ view }: { view: WebsiteImport }) {
  const { t, tp } = useI18n();
  const stage = importStage(view);
  const percent = importPercent(view);
  const host = siteHost(view.url);
  const stageText =
    stage === "queued"
      ? t("knowledge.website.queued")
      : stage === "opening"
        ? t("knowledge.website.opening", { host })
        : t("knowledge.website.reading", { current: currentPage(view), total: view.pages_planned });

  return (
    <div className="space-y-4" data-testid="website-import-progress">
      <div className="flex items-center gap-4">
        <PageStack isReading={stage !== "queued"} />
        <div className="min-w-0 flex-1">
          <p className="font-medium text-ink">{t("knowledge.website.progressLabel")}</p>
          <p className="truncate text-sm text-ink-muted" dir="ltr">
            {host}
          </p>
        </div>
      </div>
      <div
        role="progressbar"
        aria-label={t("knowledge.website.progressLabel")}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        aria-valuetext={stageText}
        className="relative h-2.5 overflow-hidden rounded-full bg-surface-muted ring-1 ring-line/60"
      >
        <div
          className={cn(
            "absolute inset-y-0 start-0 rounded-full bg-accent-solid shadow-[0_0_16px_var(--accent-solid)]",
            "transition-[width] duration-700 ease-out",
          )}
          style={{ width: `${percent}%` }}
        >
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/35 to-transparent motion-safe:animate-bar-glint" />
        </div>
      </div>
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 text-sm" aria-live="polite">
        <span className="text-ink">{stageText}</span>
        <span className="text-ink-muted">{tp("knowledge.website.found", view.items_found)}</span>
      </div>
      <p className="text-sm text-ink-subtle">{t("knowledge.website.leaveHint")}</p>
    </div>
  );
}
