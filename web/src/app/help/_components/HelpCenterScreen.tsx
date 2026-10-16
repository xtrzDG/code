"use client";

import Link from "next/link";
import { useEffect, useId, useState } from "react";

import { IconChevronRight, IconPulse, IconSearch, IconSparkles, IconX } from "@/components/icons";
import { HelpExtras } from "@/components/help/HelpExtras";
import { useHelpCenter, type HelpCenter } from "@/components/help/useHelp";
import { Card, ErrorState, Input, LoadingRegion, PageHeader, SkeletonCardList } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { helpArticlePath, STATUS_PATH, WHATS_NEW_PATH } from "@/lib/help/helpTopics";

import { HelpSearchResults } from "./HelpSearchResults";

const SEARCH_DELAY_MS = 250;

/** The help center: search, the articles by topic, and support. */
export function HelpCenterScreen({ initial, signedIn }: { initial: HelpCenter | null; signedIn: boolean }) {
  const { t } = useI18n();
  const searchId = useId();
  const center = useHelpCenter();
  const data = center.data ?? initial ?? undefined;
  const [text, setText] = useState("");
  const [query, setQuery] = useState("");

  useEffect(() => {
    const timer = window.setTimeout(() => setQuery(text.trim()), SEARCH_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [text]);

  return (
    <div className="space-y-8">
      <PageHeader title={t("helpCenter.title")} description={t("helpCenter.description")} />

      <form role="search" onSubmit={(event) => { event.preventDefault(); setQuery(text.trim()); }} className="relative">
        <label htmlFor={searchId} className="sr-only">
          {t("helpCenter.searchLabel")}
        </label>
        <IconSearch className="pointer-events-none absolute start-3.5 top-1/2 size-5 -translate-y-1/2 text-ink-subtle" aria-hidden />
        <Input
          id={searchId}
          type="search"
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder={t("helpCenter.searchPlaceholder")}
          maxLength={120}
          autoComplete="off"
          className="h-12 ps-11 pe-11 text-base"
        />
        {text ? (
          <button
            type="button"
            onClick={() => { setText(""); setQuery(""); }}
            aria-label={t("helpCenter.clearSearch")}
            className="absolute end-1.5 top-1/2 flex size-9 -translate-y-1/2 cursor-pointer items-center justify-center rounded-full text-ink-subtle hover:bg-surface-muted hover:text-ink"
          >
            <IconX className="size-4" aria-hidden />
          </button>
        ) : null}
      </form>

      {query ? (
        <HelpSearchResults query={query} />
      ) : center.error && !data ? (
        <Card>
          <ErrorState error={center.error} onRetry={center.reload} />
        </Card>
      ) : !data ? (
        <LoadingRegion label={t("common.loading")}>
          <SkeletonCardList cards={4} />
        </LoadingRegion>
      ) : (
        <div className="space-y-8">
          {data.topics.map((topic) => (
            <section key={topic.topic} aria-labelledby={`topic-${topic.topic}`} className="space-y-3">
              <h2 id={`topic-${topic.topic}`} className="text-base font-semibold text-ink">
                {t(`helpCenter.topics.${topic.topic}`)}
              </h2>
              <ul className="grid gap-3 sm:grid-cols-2">
                {topic.articles.map((article) => (
                  <li key={article.slug}>
                    <Link
                      href={helpArticlePath(article.slug)}
                      className="motion-lift flex h-full items-start gap-3 rounded-2xl border border-line bg-surface p-4 hover:border-line-strong"
                    >
                      <span className="min-w-0 flex-1 space-y-1">
                        <span className="block font-medium text-ink">{article.title}</span>
                        <span className="block text-sm text-ink-muted">{article.summary}</span>
                      </span>
                      <IconChevronRight className="mt-0.5 size-4 shrink-0 text-ink-subtle rtl:rotate-180" aria-hidden />
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}

      <nav aria-label={t("helpCenter.support.title")} className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
        <Link href={WHATS_NEW_PATH} className="inline-flex items-center gap-2 font-medium text-accent hover:underline">
          <IconSparkles className="size-4" aria-hidden />
          {t("helpCenter.support.whatsNew")}
        </Link>
        <Link href={STATUS_PATH} className="inline-flex items-center gap-2 font-medium text-accent hover:underline">
          <IconPulse className="size-4" aria-hidden />
          {t("helpCenter.support.status")}
        </Link>
      </nav>

      <HelpExtras signedIn={signedIn} />
    </div>
  );
}
