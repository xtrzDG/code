"use client";

import { useRef } from "react";

import { FadeIn } from "@/components/motion";
import { Alert } from "@/components/ui";
import { useTheme } from "@/components/theme/ThemeProvider";
import { useI18n } from "@/i18n/client";

import { useTurnstile } from "../_lib/useTurnstile";

/**
 * "One more step": the Cloudflare Turnstile check the API asked for before
 * it sends a code. Its token sends the request again at once.
 */
export function BotCheck({
  siteKey,
  isRetry,
  onToken,
}: {
  siteKey: string;
  isRetry: boolean;
  onToken: (token: string) => void;
}) {
  const { t, locale } = useI18n();
  const { theme } = useTheme();
  const container = useRef<HTMLDivElement>(null);
  const status = useTurnstile(container, { siteKey, theme, locale, onToken });

  return (
    <FadeIn
      role="group"
      aria-labelledby="bot-check-title"
      className="mt-5 space-y-3 rounded-xl border border-line bg-surface-muted p-4"
    >
      <div className="space-y-1">
        <p id="bot-check-title" className="text-sm font-semibold text-ink">
          {t("auth.botCheck.title")}
        </p>
        <p className="text-sm text-ink-muted" aria-live="polite">
          {t(isRetry ? "auth.botCheck.failed" : "auth.botCheck.hint")}
        </p>
      </div>
      {/* The widget keeps its place while it loads; a failed load shows why instead. */}
      <div ref={container} className={status === "unavailable" ? "hidden" : "min-h-[65px]"} />
      {status === "unavailable" ? <Alert tone="warning">{t("auth.botCheck.unavailable")}</Alert> : null}
    </FadeIn>
  );
}
