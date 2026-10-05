"use client";

import Link from "next/link";

import { useI18n } from "@/i18n/client";
import { legalPath, localeHomePath, type LegalPage } from "@/lib/publicSite/paths";

import { BotCheck } from "./_components/BotCheck";
import { CodeForm } from "./_components/CodeForm";
import { DestinationForm } from "./_components/DestinationForm";
import { SecondStepForm } from "./_components/SecondStepForm";
import { useLoginFlow } from "./_lib/useLoginFlow";

/** The public documents the sign-in card links to, under the "about" link. */
const LOGIN_LEGAL_PAGES: readonly LegalPage[] = ["terms", "privacy", "security", "contact"];

/**
 * Sign-in by phone (any country) or e-mail with a 6-digit code. New
 * visitors get an account automatically. When the API asks for it (a risky
 * request), a Cloudflare Turnstile check comes first; people with an
 * authenticator app (and platform admins) take a second step. The steps
 * live in `_components/`, the state in `_lib/useLoginFlow.ts`.
 */
export function LoginScreen({ next, sessionExpired }: { next: string; sessionExpired: boolean }) {
  const { t, locale } = useI18n();
  const flow = useLoginFlow(next);

  return (
    <div className="w-full max-w-sm">
      <div className="rounded-2xl border border-line bg-surface p-6 sm:p-7">
        {flow.secondStep ? (
          <SecondStepForm
            step={flow.secondStep}
            next={next}
            account={flow.destinationLabel}
            onStartOver={flow.changeDestination}
          />
        ) : flow.challenge ? (
          <CodeForm flow={flow} challenge={flow.challenge} />
        ) : (
          <DestinationForm flow={flow} sessionExpired={sessionExpired} />
        )}
        {flow.botCheck ? (
          <BotCheck
            key={flow.botCheck.attempt}
            siteKey={flow.botCheck.siteKey}
            isRetry={flow.botCheck.isRetry}
            onToken={(token) => void flow.passBotCheck(token)}
          />
        ) : null}
      </div>
      <p className="mt-5 text-center text-sm">
        <Link
          href={localeHomePath(locale)}
          className="text-ink-muted underline-offset-4 transition-colors hover:text-ink hover:underline"
        >
          {t("auth.aboutLink")}
        </Link>
      </p>
      <nav aria-label={t("legalPages.footerLabel")} className="mt-3">
        <ul className="flex flex-wrap justify-center gap-x-4 gap-y-1 text-xs" data-testid="login-legal-links">
          {LOGIN_LEGAL_PAGES.map((page) => (
            <li key={page}>
              <Link href={legalPath(locale, page)} className="text-ink-subtle underline-offset-4 transition-colors hover:text-ink hover:underline">
                {t(`legalPages.nav.${page}`)}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}
