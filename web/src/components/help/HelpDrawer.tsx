"use client";

import { usePathname } from "next/navigation";

import { IconArrowLeft, IconChevronRight } from "@/components/icons";
import { Button, ButtonLink, Drawer, ErrorState, LoadingRegion, SkeletonText } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";
import { helpArticlePath } from "@/lib/help/helpTopics";
import { businessLocation } from "@/lib/navigation";

import { HelpMarkdown } from "./HelpMarkdown";
import { SupportContacts } from "./SupportContacts";
import { useHelpArticle, type HelpArticle } from "./useHelp";

/** One article over the page: its text, what to read next, and how to reach support. */
export function HelpDrawer({
  slug,
  canGoBack,
  onOpen,
  onBack,
  onClose,
}: {
  slug: string | null;
  canGoBack: boolean;
  onOpen: (slug: string) => void;
  onBack: () => void;
  onClose: () => void;
}) {
  const { t } = useI18n();
  const article = useHelpArticle(slug);
  const data = article.data?.slug === slug ? article.data : undefined;

  return (
    <Drawer
      open={slug !== null}
      onClose={onClose}
      title={data?.title ?? t("helpCenter.drawerTitle")}
      description={data?.summary}
      footer={
        slug ? (
          <>
            {canGoBack ? (
              <Button variant="ghost" size="sm" leadingIcon={<IconArrowLeft className="size-4" aria-hidden />} onClick={onBack} className="me-auto">
                {t("helpCenter.back")}
              </Button>
            ) : null}
            <ButtonLink href={helpArticlePath(slug)} variant="secondary" size="sm" onClick={onClose}>
              {t("helpCenter.openInCenter")}
            </ButtonLink>
          </>
        ) : null
      }
    >
      {article.error && !data ? (
        <ErrorState error={article.error} onRetry={article.reload} />
      ) : !data ? (
        <LoadingRegion label={t("common.loading")}>
          <SkeletonText lines={8} />
        </LoadingRegion>
      ) : (
        <ArticleBody key={data.slug} article={data} onOpen={onOpen} onClose={onClose} />
      )}
    </Drawer>
  );
}

function ArticleBody({ article, onOpen, onClose }: { article: HelpArticle; onOpen: (slug: string) => void; onClose: () => void }) {
  const { t, locale } = useI18n();
  const businessId = businessLocation(usePathname())?.businessId ?? null;
  return (
    <div className="space-y-6">
      {article.language !== locale ? (
        <p className="rounded-lg bg-surface-muted px-3 py-2 text-xs text-ink-muted">
          {t("helpCenter.otherLanguage", { language: languageName(article.language, locale) })}
        </p>
      ) : null}
      <HelpMarkdown source={article.markdown} lang={article.language} businessId={businessId} onArticle={onOpen} onLeave={onClose} />

      {article.related.length > 0 ? (
        <section aria-labelledby="help-related" className="space-y-2">
          <h3 id="help-related" className="text-sm font-semibold text-ink">
            {t("helpCenter.related")}
          </h3>
          <ul className="space-y-1">
            {article.related.map((card) => (
              <li key={card.slug}>
                <button
                  type="button"
                  onClick={() => onOpen(card.slug)}
                  className="motion-press flex w-full cursor-pointer items-center gap-3 rounded-xl border border-line px-3 py-2.5 text-start hover:bg-surface-muted"
                >
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-medium text-ink">{card.title}</span>
                    <span className="block text-xs text-ink-muted">{card.summary}</span>
                  </span>
                  <IconChevronRight className="size-4 shrink-0 text-ink-subtle rtl:rotate-180" aria-hidden />
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section aria-labelledby="help-stuck" className="space-y-2 rounded-xl bg-surface-muted p-4">
        <h3 id="help-stuck" className="text-sm font-semibold text-ink">
          {t("helpCenter.stillStuck")}
        </h3>
        <p className="text-sm text-ink-muted">{t("helpCenter.stillStuckLead")}</p>
        <SupportContacts variant="buttons" />
      </section>
    </div>
  );
}
