"use client";

/**
 * The end of the tunnel: confetti and a burst of light, "Your assistant is
 * live!", the assistant's card, its link to share (copy, open) and a QR
 * code to try it from a phone, a few next steps, and "Open my assistant"
 * into the cabinet.
 */

import Link from "next/link";
import { useEffect, useRef } from "react";

import { displayUrl } from "@/app/b/[businessId]/assistant/channels/_lib/share";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconArrowRight, IconBook, IconExternal, IconInbox, IconPlug } from "@/components/icons";
import { Button, buttonClasses } from "@/components/ui";
import { CopyButton } from "@/components/workspace/CopyButton";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

import { QrImage } from "../QrImage";
import type { StepContext } from "../flow/stepContext";
import { AssistantCard } from "./AssistantCard";
import { Confetti } from "./Confetti";
import { useFinale } from "./useFinale";

const PANEL = "rounded-3xl border border-line bg-surface/85 p-5 backdrop-blur-md sm:p-6";

export function FinaleScreen({ ctx }: { ctx: StepContext }) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const finale = useFinale(ctx);
  const heading = useRef<HTMLHeadingElement>(null);
  const next = [
    { key: "channels", href: businessPath(ctx.businessId, "assistant/channels"), icon: IconPlug },
    { key: "knowledge", href: businessPath(ctx.businessId, "assistant/knowledge"), icon: IconBook },
    { key: "messages", href: businessPath(ctx.businessId, "messages"), icon: IconInbox },
  ] as const;

  useEffect(() => {
    heading.current?.focus({ preventScroll: true });
  }, []);

  return (
    <div className="mx-auto w-full max-w-5xl">
      <Confetti />
      <div className="text-center">
        <h1 ref={heading} tabIndex={-1} className="text-4xl leading-tight font-semibold tracking-tight text-balance text-ink outline-none! sm:text-5xl">
          {t("tunnelLaunch.finale.title")}
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-lg text-pretty text-ink-muted">{t("tunnelLaunch.finale.text", { business: business.name })}</p>
      </div>

      <div className="mt-10 grid gap-5 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <div className="space-y-5 [perspective:1200px]">
          <AssistantCard name={business.name} languages={business.languages} channels={finale.channels} />
          <section aria-labelledby="finale-next" className={PANEL}>
            <h2 id="finale-next" className="text-base font-semibold text-ink">
              {t("tunnelLaunch.finale.nextTitle")}
            </h2>
            <ul className="mt-3 space-y-1">
              {next.map(({ key, href, icon: Icon }) => (
                <li key={key}>
                  <Link href={href} className="group flex items-center gap-3 rounded-xl px-2 py-2 text-sm text-ink transition-colors hover:bg-surface-muted">
                    <Icon className="size-4 text-accent" aria-hidden />
                    <span className="flex-1">{t(`tunnelLaunch.finale.next.${key}`)}</span>
                    <IconArrowRight className="size-4 text-ink-subtle transition-transform group-hover:translate-x-0.5 rtl:-scale-x-100" aria-hidden />
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        </div>

        <div className="space-y-5">
          <section aria-labelledby="finale-share" className={PANEL}>
            <h2 id="finale-share" className="text-base font-semibold text-ink">
              {t("tunnelLaunch.finale.shareTitle")}
            </h2>
            <p className="mt-1 text-sm text-ink-muted">{t("tunnelLaunch.finale.shareText")}</p>
            {finale.shareUrl ? (
              <>
                <p className="mt-4 truncate rounded-xl bg-surface-muted px-3 py-2.5 font-mono text-sm text-ink" dir="ltr">
                  {displayUrl(finale.shareUrl)}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <CopyButton value={finale.shareUrl} label={t("tunnelLaunch.finale.copy")} variant="primary" />
                  <a href={finale.shareUrl} target="_blank" rel="noopener noreferrer" className={buttonClasses({ variant: "secondary", size: "sm" })}>
                    <IconExternal className="size-4" aria-hidden />
                    <span>{t("tunnelLaunch.finale.openChat")}</span>
                  </a>
                </div>
              </>
            ) : finale.isShareLoading ? null : (
              <p className="mt-4 text-sm text-ink-muted">{t("tunnelLaunch.finale.noLink")}</p>
            )}
          </section>

          {finale.phoneUrl ? (
            <section aria-labelledby="finale-phone" className={`${PANEL} flex items-center gap-5`}>
              <QrImage value={finale.phoneUrl} label={t("tunnelLaunch.finale.qrAlt", { link: displayUrl(finale.phoneUrl) })} className="size-32 shrink-0" />
              <div className="min-w-0">
                <h2 id="finale-phone" className="text-base font-semibold text-ink">
                  {t("tunnelLaunch.finale.phoneTitle")}
                </h2>
                <p className="mt-1 text-sm text-ink-muted">{t("tunnelLaunch.finale.phoneText")}</p>
              </div>
            </section>
          ) : null}
        </div>
      </div>

      <div className="mt-10 flex justify-center pb-[max(1.5rem,env(safe-area-inset-bottom))]">
        <Button
          size="lg"
          onClick={finale.openCabinet}
          trailingIcon={<IconArrowRight className="size-4 rtl:-scale-x-100" aria-hidden />}
          className="min-w-56 shadow-[0_18px_40px_-16px_var(--accent-solid)]"
        >
          {t("tunnelLaunch.finale.open")}
        </Button>
      </div>
    </div>
  );
}
