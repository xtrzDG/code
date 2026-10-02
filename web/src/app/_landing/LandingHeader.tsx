import { ButtonLink } from "@/components/ui";
import { TopBar } from "@/components/shell/TopBar";
import type { Translator } from "@/i18n/translate";
import { LOGIN_PATH } from "@/lib/navigation";

/** The shared top bar with anchors to the page's sections (wide screens) and "Sign in". */
export function LandingHeader({ t }: { t: Translator["t"] }) {
  const linkClass = "rounded-md px-2.5 py-1.5 text-sm text-ink-muted transition-colors hover:text-ink";
  return (
    <TopBar
      actions={
        <>
          <nav aria-label={t("landing.nav.label")} className="mr-2 hidden items-center lg:flex">
            <a href="#how" className={linkClass}>
              {t("landing.nav.how")}
            </a>
            <a href="#pricing" className={linkClass}>
              {t("landing.nav.pricing")}
            </a>
            <a href="#faq" className={linkClass}>
              {t("landing.nav.faq")}
            </a>
          </nav>
          <ButtonLink href={LOGIN_PATH} size="sm" variant="secondary" className="max-[359px]:hidden">
            {t("landing.nav.signIn")}
          </ButtonLink>
        </>
      }
    />
  );
}
