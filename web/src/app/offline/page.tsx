import type { Metadata } from "next";

import { IconRefresh } from "@/components/icons";
import { getI18n } from "@/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: t("app.offlineTitle") };
}

/**
 * What the service worker (public/sw.js) shows when a page cannot be loaded
 * without a connection. It keeps a copy from the last time the cabinet was
 * open, in that interface language and theme. Plain HTML that works without
 * scripts: "Try again" loads the address the person wanted again.
 */
export default async function OfflinePage() {
  const { t } = await getI18n();
  return (
    <main className="relative flex min-h-dvh items-center justify-center overflow-hidden px-6 py-12">
      <div aria-hidden className="landing-aurora -z-10">
        <span />
        <span />
        <span />
      </div>
      <div className="w-full max-w-md rounded-3xl border border-line bg-surface/90 p-8 text-center shadow-2xl backdrop-blur">
        <div className="mx-auto mb-6 flex size-14 items-center justify-center rounded-2xl bg-accent-solid text-on-accent shadow-[0_12px_30px_-10px_var(--accent-solid)]">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" className="size-7" aria-hidden>
            <path d="M2 8.8a15 15 0 0 1 20 0M5.5 12.4a10 10 0 0 1 13 0M9 16a5 5 0 0 1 6 0M12 20h.01M3 3l18 18" />
          </svg>
        </div>
        <h1 className="text-xl font-semibold tracking-tight text-ink">{t("app.offlineTitle")}</h1>
        <p className="mt-2 text-sm text-ink-muted">{t("app.offlineDescription")}</p>
        {/* A form without an action loads the address it is on again: no script needed. */}
        <form className="mt-6">
          <button
            type="submit"
            className="inline-flex h-11 cursor-pointer items-center gap-2 rounded-lg bg-accent-solid px-5 text-[0.9375rem] font-medium text-on-accent transition-colors hover:bg-accent-solid-hover"
          >
            <IconRefresh className="size-4" aria-hidden />
            {t("app.offlineRetry")}
          </button>
        </form>
      </div>
    </main>
  );
}
