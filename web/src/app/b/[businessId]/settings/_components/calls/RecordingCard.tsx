"use client";

import type { ReactNode } from "react";

import { Card } from "@/components/ui";
import { useI18n } from "@/i18n/client";

/**
 * The recording of calls (off unless the owner turns it on) and what
 * callers hear at the start of every call: the recording notice while it
 * is on, and always where the privacy notice is. The switch itself is the
 * form's (`switchRow`).
 */
export function RecordingCard({ isRecording, switchRow }: { isRecording: boolean; switchRow: ReactNode }) {
  const { t } = useI18n();
  return (
    <Card title={t("callSettings.recording.title")} description={t("callSettings.recording.description")}>
      <div className="space-y-5">
        {switchRow}
        <div className="border-t border-line pt-4">
          <h3 className="text-sm font-semibold text-ink">{t("callSettings.recording.noticeTitle")}</h3>
          <blockquote className="mt-2 rounded-xl border border-line bg-surface-muted p-3 text-sm text-ink">
            {isRecording ? `${t("callSettings.recording.noticeRecorded")} ` : null}
            {t("callSettings.recording.noticePrivacy")}
          </blockquote>
          <p className="mt-2 text-sm text-ink-muted">{t("callSettings.recording.noticeHint")}</p>
        </div>
      </div>
    </Card>
  );
}
