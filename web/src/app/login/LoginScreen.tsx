"use client";

import Link from "next/link";

import { useI18n } from "@/i18n/client";

import { CodeForm } from "./_components/CodeForm";
import { DestinationForm } from "./_components/DestinationForm";
import { useLoginFlow } from "./_lib/useLoginFlow";

/**
 * Sign-in by phone (any country) or e-mail with a 6-digit code. New
 * visitors get an account automatically. The steps live in
 * `_components/`, the state in `_lib/useLoginFlow.ts`.
 */
export function LoginScreen({ next, sessionExpired }: { next: string; sessionExpired: boolean }) {
  const { t } = useI18n();
  const flow = useLoginFlow(next);

  return (
    <div className="w-full max-w-sm">
      <div className="rounded-2xl border border-line bg-surface p-6 sm:p-7">
        {flow.challenge ? (
          <CodeForm flow={flow} challenge={flow.challenge} />
        ) : (
          <DestinationForm flow={flow} sessionExpired={sessionExpired} />
        )}
      </div>
      <p className="mt-5 text-center text-sm">
        <Link href="/" className="text-ink-muted underline-offset-4 transition-colors hover:text-ink hover:underline">
          {t("auth.aboutLink")}
        </Link>
      </p>
    </div>
  );
}
