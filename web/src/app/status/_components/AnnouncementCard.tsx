"use client";

import { Badge } from "@/components/ui";
import { useIsClient } from "@/components/workspace/useIsClient";
import { useI18n } from "@/i18n/client";
import { formatDateTime } from "@/lib/format";
import { listFormat } from "@/lib/intl/formatters";
import { ANNOUNCEMENT_TONES, type Announcement } from "@/lib/help/platformStatus";

/** One announcement of the team: its level, text, the parts it affects and its times (in the reader's time zone). */
export function AnnouncementCard({ announcement }: { announcement: Announcement }) {
  const { t, locale } = useI18n();
  const isClient = useIsClient();
  const when = (micros: number) => formatDateTime(micros, { locale });
  const components = listFormat(locale, { type: "conjunction" }).format(
    announcement.components.map((component) => t(`platformStatus.components.${component}`)),
  );
  const times = isClient
    ? [
        announcement.is_scheduled
          ? t("platformStatus.starts", { time: when(announcement.starts_at) })
          : t("platformStatus.since", { time: when(announcement.starts_at) }),
        announcement.resolved_at
          ? t("platformStatus.resolved", { time: when(announcement.resolved_at) })
          : announcement.expected_end_at
            ? t("platformStatus.expectedEnd", { time: when(announcement.expected_end_at) })
            : null,
        t("platformStatus.updated", { time: when(announcement.updated_at) }),
      ].filter((text): text is string => text !== null)
    : [];

  return (
    <article data-announcement-card={announcement.id} className="space-y-2 rounded-2xl border border-line bg-surface p-4">
      <p className="flex flex-wrap items-center gap-2">
        <Badge tone={announcement.resolved_at ? "neutral" : ANNOUNCEMENT_TONES[announcement.level]}>
          {t(`platformStatus.announcementLevels.${announcement.level}`)}
        </Badge>
        {announcement.is_scheduled ? <Badge tone="info">{t("platformStatus.scheduled")}</Badge> : null}
      </p>
      <p className="break-words text-ink" lang={announcement.language} dir="auto">
        {announcement.text}
      </p>
      {announcement.components.length > 0 ? (
        <p className="text-sm text-ink-muted">{t("platformStatus.affects", { components })}</p>
      ) : null}
      {times.length > 0 ? (
        <p className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-subtle">
          {times.map((text) => (
            <span key={text}>{text}</span>
          ))}
        </p>
      ) : null}
    </article>
  );
}
