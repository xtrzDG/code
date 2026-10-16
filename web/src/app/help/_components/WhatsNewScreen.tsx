"use client";

import Link from "next/link";
import { useEffect } from "react";

import { useHelpProgress } from "@/components/help/useHelp";
import { IconArrowLeft } from "@/components/icons";
import { Badge, PageHeader } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { formatDate } from "@/lib/format";
import { entryDay, newestFirst, newestKey, unreadKeys } from "@/lib/help/changelog";
import { HELP_PATH } from "@/lib/help/helpTopics";

import { CHANGELOG } from "../../../../content/changelog";

const ENTRIES = newestFirst(CHANGELOG);

/** "What's new", newest first; `readKey` is the newest entry this person had read before the page opened. */
export function WhatsNewScreen({ signedIn, readKey }: { signedIn: boolean; readKey: string | null }) {
  const { t, locale } = useI18n();
  const { markChangelogRead } = useHelpProgress(false);
  const unread = signedIn ? unreadKeys(ENTRIES, readKey) : [];
  const newest = newestKey(ENTRIES);

  // Once per visit: marking read changes nothing on this page (the badges show what was new on arrival).
  useEffect(() => {
    if (signedIn && newest && newest !== readKey) {
      void markChangelogRead(newest);
    }
  }, [signedIn, newest, readKey, markChangelogRead]);

  return (
    <div className="space-y-8">
      <Link href={HELP_PATH} className="inline-flex items-center gap-2 text-sm font-medium text-accent hover:underline">
        <IconArrowLeft className="size-4 rtl:rotate-180" aria-hidden />
        {t("helpCenter.allArticles")}
      </Link>
      <PageHeader title={t("changelog.title")} description={t("changelog.description")} />
      <ol className="space-y-4">
        {ENTRIES.map((entry) => {
          const text = entry.texts[locale];
          const day = entryDay(entry);
          return (
            <li key={entry.key}>
              <article aria-labelledby={`entry-${entry.key}`} className="space-y-2 rounded-2xl border border-line bg-surface p-5">
                <p className="flex flex-wrap items-center gap-2 text-sm text-ink-subtle">
                  {day ? <time dateTime={day.toISOString().slice(0, 10)}>{formatDate(day, { locale, timeZone: "UTC", dateStyle: "long" })}</time> : null}
                  {unread.includes(entry.key) ? <Badge tone="accent">{t("changelog.newBadge")}</Badge> : null}
                </p>
                <h2 id={`entry-${entry.key}`} className="text-lg font-semibold text-ink">
                  {text.title}
                </h2>
                {text.body.map((paragraph, index) => (
                  <p key={index} className="text-sm leading-relaxed text-ink-muted">
                    {paragraph}
                  </p>
                ))}
              </article>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
