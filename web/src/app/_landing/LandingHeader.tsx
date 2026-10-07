import { TopBar } from "@/components/shell/TopBar";
import type { Translator } from "@/i18n/translate";
import { LOGIN_PATH } from "@/lib/navigation";

import { CabinetButtonLink } from "./CabinetLink";

/**
 * The shared top bar with anchors to the landing page's sections (wide
 * screens) and "Sign in". `home` is where those sections are: "" on the
 * landing page itself, its address ("/ru") on the other public pages.
 */
export function LandingHeader({ t, home = "" }: { t: Translator["t"]; home?: string }) {
  const linkClass = "rounded-md px-2.5 py-1.5 text-sm text-ink-muted transition-colors hover:text-ink";
  return (
    <TopBar
      actions={
        <>
          <nav aria-label={t("landing.nav.label")} className="me-2 hidden items-center lg:flex">
            <a href={`${home}#how`} className={linkClass}>
              {t("landing.nav.how")}
            </a>
            <a href={`${home}#pricing`} className={linkClass}>
              {t("landing.nav.pricing")}
            </a>
            <a href={`${home}#faq`} className={linkClass}>
              {t("landing.nav.faq")}
            </a>
          </nav>
          <CabinetButtonLink href={LOGIN_PATH} size="sm" variant="secondary" className="max-[359px]:hidden">
            {t("landing.nav.signIn")}
          </CabinetButtonLink>
        </>
      }
    />
  );
}
