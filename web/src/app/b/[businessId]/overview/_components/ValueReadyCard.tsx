"use client";

import Link from "next/link";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { IconArrowRight, IconExternal, IconSparkles } from "@/components/icons";
import { QrImage } from "@/components/setup/QrImage";
import { buttonClasses } from "@/components/ui";
import { formatWholeMoney, type ValueModel } from "@/components/value/valueModel";
import { CopyButton } from "@/components/workspace/CopyButton";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { formatNumber } from "@/lib/format";
import { businessPath, inboxPath } from "@/lib/navigation";

import { heroPeriodText, TrialLine } from "./ValueHeroParts";

/** The numbers of the labelled sample: what a busy month of a small business shows. */
const SAMPLE = { bookings: 12, afterHours: 5, hours: 3 } as const;

/** "cafe.example/c/mtsvane" from "https://cafe.example/c/mtsvane": the link as people read it. */
function displayUrl(url: string): string {
  return url.replace(/^https?:\/\//, "").replace(/\/$/, "");
}

/**
 * Day 0 of the owner's hero: the assistant is live but has nothing to
 * count yet (live for under a day, or no conversation since the launch).
 * Instead of zeros presented as value, it says the assistant is ready,
 * shows a labelled sample of what will appear, and hands over the chat
 * page (link and QR) to try it or send it to customers.
 */
export function ValueReadyCard({ model, isPlaceholder }: { model: ValueModel; isPlaceholder: boolean }) {
  const { t, tp, locale } = useI18n();
  const businessId = model.business_id;
  const share = useQuery(queryKeys.channels.share(businessId, ""), () =>
    api.GET("/v1/businesses/{business_id}/share-links", { params: { path: { business_id: businessId } } }),
  );
  const shareUrl = share.data?.hosted_chat_url ?? null;
  const number = (value: number) => formatNumber(value, locale);
  const check = model.average_check_minor ?? model.typical_check_minor ?? null;
  const started = model.current.conversation_count;

  return (
    <section
      aria-labelledby="value-ready-title"
      aria-busy={isPlaceholder || undefined}
      data-value-stage="ready"
      className={cn(
        "relative isolate overflow-hidden rounded-3xl border border-accent/25 bg-surface p-4 shadow-sm transition-opacity sm:p-6",
        isPlaceholder && "opacity-60",
      )}
    >
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute -end-20 -top-28 size-80 rounded-full bg-accent-solid/20 blur-3xl motion-safe:animate-drift" />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="value-ready-title" className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-sm font-semibold text-ink">
          <IconSparkles className="size-4 text-accent" aria-hidden />
          {t("value.ready.title")}
          <span aria-hidden className="font-normal text-ink-subtle max-sm:hidden">
            ·
          </span>
          <span className="font-normal text-ink-muted max-sm:basis-full max-sm:ps-6">{heroPeriodText(model, locale, t)}</span>
        </h2>
        <TrialLine model={model} />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
        <div className="flex flex-col gap-4">
          <div>
            <p className="text-2xl font-semibold tracking-tight text-ink sm:text-3xl">{t("value.ready.lead")}</p>
            <p className="mt-2 max-w-prose text-sm text-ink-muted">{t("value.ready.body")}</p>
            {started > 0 ? (
              <p className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-ink">
                <span>{tp("value.ready.started", started, { count: number(started) })}</span>
                <Link href={inboxPath(businessId, "all")} className="inline-flex items-center gap-1 font-medium text-accent hover:underline">
                  {t("value.ready.openInbox")}
                  <IconArrowRight className="size-4 rtl:-scale-x-100" aria-hidden />
                </Link>
              </p>
            ) : null}
          </div>

          <figure data-value-sample="" className="relative rounded-2xl border border-dashed border-line-strong bg-surface-muted/50 p-4">
            <span className="absolute end-3 top-3 rounded-full bg-surface px-2 py-0.5 text-xs font-medium text-ink-muted ring-1 ring-line">
              {t("value.ready.sampleLabel")}
            </span>
            <div aria-hidden className="select-none opacity-70">
              <p className="text-sm font-medium text-ink-muted">{t("value.hero.bookingsLabel")}</p>
              <p className="mt-1 flex flex-wrap items-baseline gap-x-3 text-3xl font-semibold tracking-tight text-ink tabular-nums">
                <span>{number(SAMPLE.bookings)}</span>
                {check !== null ? (
                  <span className="text-2xl text-accent">≈ {formatWholeMoney(check * SAMPLE.bookings, model.currency_code, locale)}</span>
                ) : null}
              </p>
              <p className="mt-2 text-sm text-ink-muted">
                {tp("value.hero.afterHours", SAMPLE.afterHours, { count: number(SAMPLE.afterHours) })}
                {" · "}
                {tp("value.hero.hoursSaved", SAMPLE.hours, { count: number(SAMPLE.hours) })}
              </p>
            </div>
            <figcaption className="mt-3 text-xs text-ink-subtle">{t("value.ready.sampleCaption")}</figcaption>
          </figure>
        </div>

        <div className="flex flex-col gap-3 rounded-2xl border border-line bg-surface/80 p-4">
          <h3 className="text-base font-semibold text-ink">{t("value.ready.shareTitle")}</h3>
          {shareUrl ? (
            <div className="flex flex-wrap items-center gap-4">
              <QrImage value={shareUrl} label={t("value.ready.qrAlt", { link: displayUrl(shareUrl) })} className="size-28 shrink-0" />
              <div className="min-w-0 flex-1 basis-40">
                <p className="text-sm text-ink-muted">{t("value.ready.shareText")}</p>
                <p className="mt-1 truncate text-sm font-medium text-ink" dir="ltr">
                  {displayUrl(shareUrl)}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <CopyButton value={shareUrl} label={t("value.ready.copy")} variant="primary" />
                  <a href={shareUrl} target="_blank" rel="noopener noreferrer" className={buttonClasses({ variant: "secondary", size: "sm" })}>
                    <IconExternal className="size-4" aria-hidden />
                    <span>{t("value.ready.open")}</span>
                  </a>
                </div>
              </div>
            </div>
          ) : share.isLoading && !share.data ? null : (
            <div className="space-y-3">
              <p className="text-sm text-ink-muted">{t("value.ready.noLink")}</p>
              <Link href={businessPath(businessId, "assistant/channels")} className={buttonClasses({ variant: "secondary", size: "sm" })}>
                {t("value.ready.connect")}
              </Link>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
