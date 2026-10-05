import Link from "next/link";
import type { ReactNode } from "react";

import type { NicheSummaryView } from "@/api/types";
import { Alert } from "@/components/ui";
import type { Locale } from "@/i18n/config";
import type { Translator } from "@/i18n/translate";
import { cn } from "@/lib/cn";
import { LEGAL_PAGES, legalPath, localeHomePath, type LegalPage } from "@/lib/publicSite/paths";

import { LandingFooter } from "../LandingFooter";
import { LandingHeader } from "../LandingHeader";

/**
 * The frame of the public legal and contact pages: the site's header and
 * footer, the list of the documents (a row on phones, a column beside the
 * text on wide screens) and, while the texts are drafts, a banner that
 * says so above the text.
 */
export function LegalShell({
  t,
  locale,
  page,
  isDraft,
  niches = null,
  children,
}: {
  t: Translator["t"];
  locale: Locale;
  page: LegalPage;
  isDraft: boolean;
  niches?: readonly NicheSummaryView[] | null;
  children: ReactNode;
}) {
  const home = localeHomePath(locale);
  return (
    <div className="flex min-h-dvh flex-col">
      <LandingHeader t={t} home={home} />
      <main id="main" className="flex-1">
        <div className="mx-auto grid w-full max-w-6xl gap-8 px-4 py-10 sm:px-6 sm:py-14 lg:grid-cols-[14rem_minmax(0,1fr)] lg:gap-12">
          <nav aria-label={t("legalPages.footerLabel")} className="min-w-0">
            <ul className="-mx-4 flex gap-1.5 overflow-x-auto px-4 pb-1 lg:mx-0 lg:flex-col lg:overflow-visible lg:px-0 lg:pb-0">
              {LEGAL_PAGES.map((item) => (
                <li key={item} className="shrink-0">
                  <Link
                    href={legalPath(locale, item)}
                    aria-current={item === page ? "page" : undefined}
                    className={cn(
                      "block rounded-lg px-3 py-1.5 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-focus",
                      item === page ? "bg-accent-soft font-medium text-accent-ink" : "text-ink-muted hover:bg-surface-muted hover:text-ink",
                    )}
                  >
                    {t(`legalPages.nav.${item}`)}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
          <div className="min-w-0 max-w-3xl space-y-6">
            {isDraft ? (
              <div data-testid="legal-draft">
                <Alert tone="warning" title={t("legalPages.draftTitle")}>
                  {t("legalPages.draftText")}
                </Alert>
              </div>
            ) : null}
            {children}
          </div>
        </div>
      </main>
      <LandingFooter t={t} locale={locale} home={home} niches={niches} />
    </div>
  );
}
