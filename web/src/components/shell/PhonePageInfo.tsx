"use client";

/**
 * The page's own corner of the phone's top bar: a dot beside the title that
 * tells whether the page is live (green and breathing; amber while the
 * connection is down), and an (i) that opens a sheet with what the page is
 * for and how fresh its data is, with "Try now" when the connection
 * dropped. Both come from what the page registered (components/ui/PhoneChrome).
 */

import { useState } from "react";

import { Sheet, usePhoneChromeSnapshot } from "@/components/ui";
import type { ChromeLive } from "@/lib/phoneChrome";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { IconInfo } from "../icons";
import { useLiveCabinet } from "./LiveEvents";
import { LiveStatusLine, useUpdatedText } from "./LiveStatus";

export function LiveDot({ live }: { live: ChromeLive }) {
  const { t } = useI18n();
  const cabinet = useLiveCabinet();
  const status = cabinet?.status ?? null;
  const updated = useUpdatedText(live.updatedAt, live.isFetching);
  if (!status) {
    return null;
  }
  const isLive = status === "live";
  const isDown = status === "reconnecting" || status === "stopped";
  const label = t("chrome.liveDot", { status: t(`live.status.${status === "stopped" ? "paused" : status}`), updated });
  return (
    <span role="img" aria-label={label} title={label} data-live-dot={status} className="relative inline-flex size-2 shrink-0">
      {isLive ? <span className="absolute inset-0 rounded-full bg-success opacity-60 motion-safe:animate-ping" /> : null}
      <span className={cn("relative inline-flex size-2 rounded-full", isLive ? "bg-success" : isDown ? "bg-warning" : "bg-ink-subtle")} />
    </span>
  );
}

/** The (i) of the top bar and its sheet; nothing when the page says nothing about itself. */
export function PageInfoButton({ title }: { title?: string }) {
  const { t } = useI18n();
  const { descriptions, live } = usePhoneChromeSnapshot();
  const [isOpen, setOpen] = useState(false);
  if (descriptions.length === 0 && !live) {
    return null;
  }
  const isSingle = descriptions.length === 1;
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label={t("chrome.pageInfo")}
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        className="motion-press -me-1 flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-full text-ink-muted hover:bg-surface-muted hover:text-ink focus-visible:outline-2 focus-visible:outline-focus"
      >
        <IconInfo className="size-5" aria-hidden />
      </button>
      <Sheet open={isOpen} onClose={() => setOpen(false)} title={title ?? t("chrome.pageInfo")}>
        <div className="space-y-4 pb-1">
          {descriptions.map((description, index) => (
            <section key={index} className="space-y-1">
              {isSingle ? null : <h3 className="text-sm font-semibold text-ink">{description.title}</h3>}
              <p className="text-[0.9375rem] leading-relaxed text-ink-muted">{description.text}</p>
            </section>
          ))}
          {live ? (
            <LiveStatusLine
              updatedAt={live.updatedAt}
              isFetching={live.isFetching}
              className={cn(descriptions.length > 0 && "border-t border-line pt-3")}
            />
          ) : null}
        </div>
      </Sheet>
    </>
  );
}
