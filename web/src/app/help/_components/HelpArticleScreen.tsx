"use client";

import Link from "next/link";

import { HelpExtras } from "@/components/help/HelpExtras";
import { HelpMarkdown } from "@/components/help/HelpMarkdown";
import { useHelpArticle, type HelpArticle } from "@/components/help/useHelp";
import { IconArrowLeft, IconChevronRight } from "@/components/icons";
import { Card, ErrorState, LoadingRegion, SkeletonText } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";
import { HELP_PATH, helpArticlePath } from "@/lib/help/helpTopics";

/** One article: its text, what to read next, and how to reach support. */
export function HelpArticleScreen({ slug, initial, signedIn }: { slug: string; initial: HelpArticle | null; signedIn: boolean }) {
  const { t, locale } = useI18n();
  const query = useHelpArticle(slug);
  const article = query.data ?? initial ?? undefined;

  return (
    <div className="space-y-8">
      <Link href={HELP_PATH} className="inline-flex items-center gap-2 text-sm font-medium text-accent hover:underline">
        <IconArrowLeft className="size-4 rtl:rotate-180" aria-hidden />
        {t("helpCenter.allArticles")}
      </Link>

      {query.error && !article ? (
        <Card>
          <ErrorState error={query.error} onRetry={query.reload} />
        </Card>
      ) : !article ? (
        <LoadingRegion label={t("common.loading")}>
          <SkeletonText lines={10} />
        </LoadingRegion>
      ) : (
        <article lang={article.language} className="space-y-6">
          <header className="space-y-2">
            <p className="text-sm font-medium text-accent">{t(`helpCenter.topics.${article.topic}`)}</p>
            <h1 className="text-2xl font-semibold tracking-tight text-ink sm:text-3xl">{article.title}</h1>
            <p className="text-base text-ink-muted">{article.summary}</p>
          </header>
          {article.language !== locale ? (
            <p className="rounded-lg bg-surface-muted px-3 py-2 text-sm text-ink-muted" lang={locale}>
              {t("helpCenter.otherLanguage", { language: languageName(article.language, locale) })}
            </p>
          ) : null}
          <HelpMarkdown source={article.markdown} businessId={null} className="text-base" />
          {article.related.length > 0 ? (
            <section aria-labelledby="related-title" className="space-y-3" lang={locale}>
              <h2 id="related-title" className="text-base font-semibold text-ink">
                {t("helpCenter.related")}
              </h2>
              <ul className="grid gap-3 sm:grid-cols-2">
                {article.related.map((card) => (
                  <li key={card.slug}>
                    <Link
                      href={helpArticlePath(card.slug)}
                      className="motion-lift flex h-full items-start gap-3 rounded-2xl border border-line bg-surface p-4 hover:border-line-strong"
                    >
                      <span className="min-w-0 flex-1 space-y-1">
                        <span className="block font-medium text-ink">{card.title}</span>
                        <span className="block text-sm text-ink-muted">{card.summary}</span>
                      </span>
                      <IconChevronRight className="mt-0.5 size-4 shrink-0 text-ink-subtle rtl:rotate-180" aria-hidden />
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </article>
      )}

      <HelpExtras signedIn={signedIn} />
    </div>
  );
}
