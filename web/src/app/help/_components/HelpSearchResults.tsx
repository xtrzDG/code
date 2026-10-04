"use client";

import Link from "next/link";

import { useHelpSearch } from "@/components/help/useHelp";
import { Card, ErrorState, LoadingRegion, SkeletonCardList } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { helpArticlePath } from "@/lib/help/helpTopics";

/** The articles that match a search, best first, with the passage that matched. */
export function HelpSearchResults({ query }: { query: string }) {
  const { t, tp } = useI18n();
  const search = useHelpSearch(query);
  const items = search.data?.items;

  if (search.error && !items) {
    return (
      <Card>
        <ErrorState error={search.error} onRetry={search.reload} />
      </Card>
    );
  }
  if (!items) {
    return (
      <LoadingRegion label={t("common.loading")}>
        <SkeletonCardList cards={3} />
      </LoadingRegion>
    );
  }
  return (
    <section aria-labelledby="help-results" className={cn("space-y-3", search.isPlaceholder && "opacity-60")}>
      <h2 id="help-results" className="text-sm font-medium text-ink-muted" aria-live="polite">
        {items.length > 0 ? tp("helpCenter.results", items.length) : t("helpCenter.noResults", { query })}
      </h2>
      <ul className="space-y-3">
        {items.map((hit) => (
          <li key={hit.slug}>
            <Link
              href={helpArticlePath(hit.slug)}
              className="motion-lift block space-y-1 rounded-2xl border border-line bg-surface p-4 hover:border-line-strong"
            >
              <span className="block text-xs font-medium text-ink-subtle">{t(`helpCenter.topics.${hit.topic}`)}</span>
              <span className="block font-medium text-ink">{hit.title}</span>
              <span className="block text-sm text-ink-muted">{hit.snippet ?? hit.summary}</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
