import Link from "next/link";

import type { NicheSummaryView } from "@/api/types";
import type { Locale } from "@/i18n/config";
import type { Translator } from "@/i18n/translate";
import { LOGIN_PATH } from "@/lib/navigation";
import { LEGAL_PAGES, legalPath, nichePath } from "@/lib/publicSite/paths";

/** How many kinds of business the footer links to (the rest are on the landing page). */
const FOOTER_NICHES = 8;

const LINK_CLASS = "text-ink-muted transition-colors hover:text-ink";

/**
 * The public site's footer: the landing page's sections, the pages of the
 * kinds of business, the legal and contact pages, and the copyright.
 * `home` is "" on the landing page itself, else its address ("/ru").
 */
export function LandingFooter({
  t,
  locale,
  home = "",
  niches = null,
}: {
  t: Translator["t"];
  locale: Locale;
  home?: string;
  niches?: readonly NicheSummaryView[] | null;
}) {
  const shown = (niches ?? []).slice(0, FOOTER_NICHES);
  return (
    <footer className="border-t border-line" data-testid="site-footer">
      <div className="mx-auto grid w-full max-w-6xl gap-8 px-4 py-10 text-sm sm:grid-cols-2 sm:px-6 lg:grid-cols-[1.2fr_1fr_1fr_1fr]">
        <div className="space-y-2">
          <p className="font-semibold text-ink">{t("common.appName")}</p>
          <p className="max-w-xs text-pretty text-ink-subtle">{t("common.tagline")}</p>
        </div>
        <nav aria-label={t("landing.nav.label")} className="space-y-3">
          <p className="font-medium text-ink">{t("landing.nav.label")}</p>
          <ul className="space-y-2">
            <li>
              <a href={`${home}#how`} className={LINK_CLASS}>
                {t("landing.nav.how")}
              </a>
            </li>
            <li>
              <a href={`${home}#pricing`} className={LINK_CLASS}>
                {t("landing.nav.pricing")}
              </a>
            </li>
            <li>
              <a href={`${home}#faq`} className={LINK_CLASS}>
                {t("landing.nav.faq")}
              </a>
            </li>
            <li>
              {/* A plain link: the cabinet page loads whole (CabinetLink.tsx). */}
              <a href={LOGIN_PATH} className={LINK_CLASS}>
                {t("landing.nav.signIn")}
              </a>
            </li>
          </ul>
        </nav>
        {shown.length > 0 ? (
          <nav aria-label={t("nichePage.breadcrumb")} className="space-y-3">
            <p className="font-medium text-ink">{t("nichePage.breadcrumb")}</p>
            <ul className="space-y-2">
              {shown.map((niche) => (
                <li key={niche.key}>
                  <Link href={nichePath(locale, niche.key)} className={LINK_CLASS}>
                    {niche.name}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        ) : null}
        <nav aria-label={t("legalPages.footerLabel")} className="space-y-3">
          <p className="font-medium text-ink">{t("legalPages.footerLabel")}</p>
          <ul className="space-y-2">
            {LEGAL_PAGES.map((page) => (
              <li key={page}>
                <Link href={legalPath(locale, page)} className={LINK_CLASS}>
                  {t(`legalPages.nav.${page}`)}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </div>
      <div className="border-t border-line">
        <p className="mx-auto w-full max-w-6xl px-4 py-5 text-xs text-ink-subtle sm:px-6">
          {t("landing.footer.rights", { year: new Date().getFullYear(), name: t("common.appName") })}
        </p>
      </div>
    </footer>
  );
}
