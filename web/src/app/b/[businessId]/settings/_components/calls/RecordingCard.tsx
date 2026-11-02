"use client";

import type { ReactNode } from "react";

import { Card } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { callerNoticeKeys } from "../../_lib/calls";

/**
 * The recording of calls (off unless the owner turns it on) and what
 * callers hear at the start of every call, as the call's greeting says it
 * (`callerNoticeKeys`): the recording notice only while it is on, and
 * always where the privacy notice is. The switch itself is the form's
 * (`switchRow`).
 */
export function RecordingCard({
  isRecording,
  businessName,
  switchRow,
}: {
  isRecording: boolean;
  businessName: string;
  switchRow: ReactNode;
}) {
  const { t } = useI18n();
  return (
    <Card title={t("callSettings.recording.title")} description={t("callSettings.recording.description")}>
      <div className="space-y-5">
        {switchRow}
        <div className="border-t border-line pt-4">
          <h3 className="text-sm font-semibold text-ink">{t("callSettings.recording.noticeTitle")}</h3>
          <blockquote className="mt-2 rounded-xl border border-line bg-surface-muted p-3 text-sm text-ink">
            {callerNoticeKeys(isRecording).map((key, index) => (
              <span key={key}>
                {index > 0 ? " " : null}
                {t(key, { business: businessName })}
              </span>
            ))}
          </blockquote>
          <p className="mt-2 text-sm text-ink-muted">{t("callSettings.recording.noticeHint")}</p>
        </div>
      </div>
    </Card>
  );
}
