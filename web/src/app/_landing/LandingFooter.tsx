import Link from "next/link";

import type { Translator } from "@/i18n/translate";
import { LOGIN_PATH } from "@/lib/navigation";

/** Copyright and the main links again. */
export function LandingFooter({ t }: { t: Translator["t"] }) {
  const linkClass = "text-ink-muted transition-colors hover:text-ink";
  return (
    <footer className="border-t border-line">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 py-8 text-sm sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <p className="text-ink-subtle">
          {t("landing.footer.rights", { year: new Date().getFullYear(), name: t("common.appName") })}
        </p>
        <nav aria-label={t("landing.nav.label")} className="flex flex-wrap gap-x-6 gap-y-2">
          <a href="#how" className={linkClass}>
            {t("landing.nav.how")}
          </a>
          <a href="#pricing" className={linkClass}>
            {t("landing.nav.pricing")}
          </a>
          <a href="#faq" className={linkClass}>
            {t("landing.nav.faq")}
          </a>
          <Link href={LOGIN_PATH} className={linkClass}>
            {t("landing.nav.signIn")}
          </Link>
        </nav>
      </div>
    </footer>
  );
}
