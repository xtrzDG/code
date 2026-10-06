"use client";

import { useState } from "react";

import type { Schema } from "@/api/types";
import { QrImage } from "@/components/setup/QrImage";
import { Button } from "@/components/ui";
import { CopyButton } from "@/components/workspace/CopyButton";
import { useI18n } from "@/i18n/client";
import { shareMessage } from "@/lib/referrals/referralLinks";

type ReferralProgramView = Schema<"ReferralProgramView">;

/**
 * The invitation link with Copy, Share (the phone's share sheet when there
 * is one) and its QR code, and how many businesses signed up, paid and
 * earned both sides their month.
 */
export function InviteLinkPanel({ view, formatCount }: { view: ReferralProgramView; formatCount: (value: number) => string }) {
  const { t } = useI18n();
  const [showsQr, setShowsQr] = useState(false);
  const link = view.invite_link ?? null;
  const canShare = typeof navigator !== "undefined" && typeof navigator.share === "function";

  const share = async () => {
    if (!link) {
      return;
    }
    try {
      await navigator.share({ text: shareMessage(t("referrals.shareText", { app: t("common.appName") }), link) });
    } catch {
      // Closing the share sheet is not an error.
    }
  };

  return (
    <div className="space-y-4">
      {link ? (
        <div className="space-y-2">
          <p className="text-xs font-medium tracking-wide text-ink-subtle uppercase">{t("referrals.linkLabel")}</p>
          <p className="rounded-lg bg-surface-muted px-3 py-2 font-mono text-sm break-all text-ink" data-testid="invite-link">
            {link}
          </p>
          <div className="flex flex-wrap gap-2">
            <CopyButton value={link} label={t("referrals.copy")} />
            {canShare ? (
              <Button variant="secondary" size="sm" onClick={() => void share()}>
                {t("referrals.share")}
              </Button>
            ) : null}
            <Button variant="ghost" size="sm" aria-expanded={showsQr} onClick={() => setShowsQr((value) => !value)}>
              {showsQr ? t("referrals.hideQr") : t("referrals.showQr")}
            </Button>
          </div>
          {showsQr ? <QrImage value={link} label={t("referrals.qrLabel")} className="size-40" /> : null}
        </div>
      ) : (
        <p className="text-sm text-ink-muted">{t("referrals.noLink")}</p>
      )}

      <dl aria-label={t("referrals.statsLabel")} className="grid grid-cols-3 gap-2">
        {(
          [
            ["invited", view.invited],
            ["paid", view.paid],
            ["rewarded", view.rewarded],
          ] as const
        ).map(([key, value]) => (
          <div key={key} className="rounded-lg border border-line px-3 py-2">
            <dt className="text-xs text-ink-subtle">{t(`referrals.${key}`)}</dt>
            <dd className="text-lg font-semibold text-ink tabular-nums">{formatCount(value)}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
