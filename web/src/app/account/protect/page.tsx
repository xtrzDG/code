import type { Metadata } from "next";

import { IconShield } from "@/components/icons";
import { TopBar } from "@/components/shell/TopBar";
import { ButtonLink, Card } from "@/components/ui";
import { getI18n } from "@/i18n/server";
import { securityPath } from "@/lib/navigation";
import { suggestionNext } from "@/lib/security/secondFactorSuggestion";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: t("security.suggestion.title") };
}

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

/**
 * Right after an owner without a second factor signs in with the login
 * code alone: set up a passkey or the authenticator app now (Account →
 * Security, then back to `next`), or put it off ("Not now", asked again at
 * the next sign-in). A business may still require one of its whole team.
 */
export default async function ProtectAccountPage({ searchParams }: PageProps<"/account/protect">) {
  const { t } = await getI18n();
  const next = suggestionNext(first((await searchParams).next));

  return (
    <div className="flex min-h-dvh flex-col">
      <TopBar signedIn />
      <main id="main" className="mx-auto w-full max-w-xl flex-1 px-4 py-8 sm:px-6 lg:py-12">
        <Card>
          <div className="space-y-4">
            <IconShield className="size-8 text-accent" aria-hidden />
            <h1 className="text-xl font-semibold text-ink">{t("security.suggestion.title")}</h1>
            <p className="text-sm text-ink-muted">{t("security.suggestion.body")}</p>
            <ul className="list-disc space-y-1 ps-5 text-sm text-ink">
              <li>{t("security.suggestion.passkey")}</li>
              <li>{t("security.suggestion.app")}</li>
            </ul>
            <div className="flex flex-wrap gap-2 pt-2">
              <ButtonLink href={securityPath({ next })}>{t("security.suggestion.setUp")}</ButtonLink>
              <ButtonLink href={next} variant="secondary">
                {t("security.suggestion.later")}
              </ButtonLink>
            </div>
            <p className="text-xs text-ink-muted">{t("security.suggestion.reminder")}</p>
          </div>
        </Card>
      </main>
    </div>
  );
}
