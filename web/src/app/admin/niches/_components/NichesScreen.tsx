"use client";

/**
 * /admin/niches: every niche template with the version of its texts in
 * force (0: the code template), how many texts it rewords, who published
 * it and whether a draft waits; each opens its editor.
 */

import Link from "next/link";

import { IconChevronRight } from "@/components/icons";
import { useViewerFormat } from "@/components/time/ViewerTimeZone";
import { Badge, Card, ErrorState, LoadingRegion, PageHeader, SkeletonCard } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { adminNichePath } from "@/lib/navigation";

import type { NicheTextStatus } from "../_lib/nicheTexts";
import { useNicheOverview } from "../_lib/useNicheTexts";

export function NichesScreen() {
  const { t, locale } = useI18n();
  const overview = useNicheOverview(locale);
  const items = overview.data?.items ?? [];

  return (
    <>
      <PageHeader title={t("adminNiches.title")} description={t("adminNiches.description")} />
      {overview.error && !overview.data ? (
        <Card>
          <ErrorState error={overview.error} onRetry={overview.reload} />
        </Card>
      ) : !overview.data ? (
        <NichesSkeleton />
      ) : (
        <Card aria-label={t("adminNiches.list")} padded={false}>
          <ul className="divide-y divide-line">
            {items.map((item) => (
              <NicheRow key={item.niche_key} item={item} language={locale} />
            ))}
          </ul>
        </Card>
      )}
    </>
  );
}

function NicheRow({ item, language }: { item: NicheTextStatus; language: string }) {
  const { t, tp } = useI18n();
  const format = useViewerFormat();
  const when = item.published_at ? format.dateTime(item.published_at) : null;
  return (
    <li>
      <Link
        href={adminNichePath(item.niche_key, language)}
        aria-label={t("adminNiches.edit", { niche: item.name })}
        className="flex items-center gap-3 px-4 py-3 hover:bg-surface-muted focus-visible:bg-surface-muted sm:px-5"
      >
        <div className="min-w-0 flex-1 space-y-1">
          <p className="font-medium text-ink">{item.name}</p>
          <div className="flex flex-wrap items-center gap-2 text-xs text-ink-muted">
            <Badge tone={item.published_version > 0 ? "accent" : "neutral"}>
              {item.published_version > 0 ? t("adminNiches.version", { version: item.published_version }) : t("adminNiches.codeTemplate")}
            </Badge>
            {item.override_count > 0 ? <span>{tp("adminNiches.reworded", item.override_count)}</span> : null}
            {item.has_draft ? <Badge tone="warning">{t("adminNiches.draft")}</Badge> : null}
            {when ? (
              <span>
                {item.published_by_name
                  ? t("adminNiches.publishedBy", { when, name: item.published_by_name })
                  : t("adminNiches.publishedAt", { when })}
              </span>
            ) : null}
          </div>
        </div>
        <IconChevronRight className="size-4 shrink-0 text-ink-subtle rtl:-scale-x-100" aria-hidden />
      </Link>
    </li>
  );
}

/** The list while it loads (also the route's loading.tsx). */
export function NichesSkeleton() {
  const { t } = useI18n();
  return (
    <LoadingRegion label={t("adminNiches.loading")}>
      <SkeletonCard lines={8} />
    </LoadingRegion>
  );
}
