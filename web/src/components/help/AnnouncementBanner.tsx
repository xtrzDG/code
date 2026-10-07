"use client";

/**
 * Over every page of the cabinet while the platform team announces
 * something (planned maintenance, a slowdown, an outage): its text in the
 * interface language, when it ends, and a link to the status page. A
 * notice, maintenance or a slowdown can be hidden in this browser until it
 * changes; an outage stays.
 */

import Link from "next/link";
import { useSyncExternalStore } from "react";

import { IconMegaphone, IconX } from "@/components/icons";
import { useViewerFormat } from "@/components/time/ViewerTimeZone";
import { Badge } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import {
  ANNOUNCEMENT_TONES,
  bannerAnnouncements,
  canDismiss,
  dismissKey,
  parseDismissed,
  type Announcement,
} from "@/lib/help/platformStatus";
import { STATUS_PATH } from "@/lib/help/helpTopics";

import { usePlatformStatus } from "./usePlatformStatus";

const STORAGE_KEY = "aw_hidden_announcements";
const CHANGE_EVENT = "aw-hidden-announcements";

function readHidden(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function subscribeHidden(onChange: () => void): () => void {
  window.addEventListener("storage", onChange);
  window.addEventListener(CHANGE_EVENT, onChange);
  return () => {
    window.removeEventListener("storage", onChange);
    window.removeEventListener(CHANGE_EVENT, onChange);
  };
}

function hide(announcement: Announcement) {
  try {
    const hidden = [...parseDismissed(readHidden()), dismissKey(announcement)];
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(hidden));
  } catch {
    // Storage blocked: hidden for this page only is not worth more.
  }
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

const FRAMES: Record<Announcement["level"], string> = {
  info: "border-info/30 bg-info-soft/70",
  maintenance: "border-info/30 bg-info-soft/70",
  degraded: "border-warning/40 bg-warning-soft/70",
  outage: "border-danger/40 bg-danger-soft/80",
};

export function AnnouncementBanner() {
  const { t } = useI18n();
  const status = usePlatformStatus();
  const hidden = parseDismissed(useSyncExternalStore(subscribeHidden, readHidden, () => null));
  const shown = bannerAnnouncements(status.data, hidden).slice(0, 2);
  if (shown.length === 0) {
    return null;
  }
  return (
    <section aria-label={t("platformStatus.banner.region")} className="space-y-2 px-4 pt-3 sm:px-6 lg:px-8 lg:pt-4">
      {shown.map((announcement) => (
        <AnnouncementRow key={announcement.id} announcement={announcement} />
      ))}
    </section>
  );
}

function AnnouncementRow({ announcement }: { announcement: Announcement }) {
  const { t } = useI18n();
  const viewer = useViewerFormat();
  const when = (micros: number) => viewer.dateTime(micros);
  const timing = announcement.is_scheduled
    ? t("platformStatus.starts", { time: when(announcement.starts_at) })
    : announcement.expected_end_at
      ? t("platformStatus.expectedEnd", { time: when(announcement.expected_end_at) })
      : null;
  return (
    <div
      data-announcement={announcement.level}
      className={cn("mx-auto flex max-w-[100rem] items-start gap-3 rounded-2xl border px-4 py-3 text-sm", FRAMES[announcement.level])}
    >
      <IconMegaphone className="mt-0.5 size-5 shrink-0 text-ink-muted" aria-hidden />
      <div className="min-w-0 flex-1 space-y-1">
        <p className="flex flex-wrap items-center gap-2">
          <Badge tone={ANNOUNCEMENT_TONES[announcement.level]}>
            {announcement.is_scheduled ? t("platformStatus.scheduled") : t(`platformStatus.announcementLevels.${announcement.level}`)}
          </Badge>
          {timing ? <span className="text-xs text-ink-muted">{timing}</span> : null}
        </p>
        <p className="break-words text-ink" lang={announcement.language} dir="auto">
          {announcement.text}{" "}
          <Link href={STATUS_PATH} className="font-medium whitespace-nowrap text-accent underline-offset-2 hover:underline">
            {t("platformStatus.banner.details")}
          </Link>
        </p>
      </div>
      {canDismiss(announcement) ? (
        <button
          type="button"
          onClick={() => hide(announcement)}
          aria-label={t("platformStatus.banner.dismiss")}
          title={t("platformStatus.banner.dismiss")}
          className="motion-press -m-1 flex size-8 shrink-0 cursor-pointer items-center justify-center rounded-full text-ink-subtle hover:bg-surface/60 hover:text-ink pointer-coarse:size-11"
        >
          <IconX className="size-4" aria-hidden />
        </button>
      ) : null}
    </div>
  );
}
