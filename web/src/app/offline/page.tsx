import type { Metadata } from "next";

import { IconRefresh } from "@/components/icons";
import { OfflineIllustration } from "@/components/illustrations";
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
        {/* The drawing fills its box (IllustrationFrame); the box gives it its size. */}
        <div className="mx-auto mb-4 w-40">
          <OfflineIllustration />
        </div>
        <h1 className="text-xl font-display tracking-tight text-ink">{t("app.offlineTitle")}</h1>
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
