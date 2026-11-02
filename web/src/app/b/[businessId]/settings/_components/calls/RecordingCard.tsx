"use client";

import type { ReactNode } from "react";

import { Card } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";

import type { CallNoticePreview } from "../../_lib/calls";

/**
 * The recording of calls (off unless the owner turns it on) and what
 * callers hear about it and about the privacy notice, in each language of
 * the business. The switch itself is the form's (`switchRow`).
 */
export function RecordingCard({
  notices,
  switchRow,
}: {
  notices: readonly CallNoticePreview[];
  switchRow: ReactNode;
}) {
  const { t, locale } = useI18n();
  return (
    <Card title={t("callSettings.recording.title")} description={t("callSettings.recording.description")}>
      <div className="space-y-5">
        {switchRow}
        <div className="border-t border-line pt-4">
          <h3 className="text-sm font-semibold text-ink">{t("callSettings.recording.noticeTitle")}</h3>
          <p className="mt-0.5 text-sm text-ink-muted">{t("callSettings.recording.noticeHint")}</p>
          <ul className="mt-3 space-y-3">
            {notices.map((notice) => (
              <li key={notice.language} className="rounded-xl border border-line p-3 text-sm">
                <p className="font-medium text-ink">{languageName(notice.language, locale)}</p>
                <p lang={notice.language} dir="auto" className="mt-1 text-ink-muted [overflow-wrap:anywhere]">
                  {notice.text}
                </p>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Card>
  );
}
