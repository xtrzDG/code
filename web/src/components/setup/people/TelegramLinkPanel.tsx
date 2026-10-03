"use client";

/**
 * The owner's one-time Telegram link: a button that opens Telegram on
 * this computer, its QR code for the phone, the code to send the bot by
 * hand, and "waiting" until the chat appears (then a check mark).
 */

import type { Schema } from "@/api/types";
import { formatLinkCode } from "@/app/b/[businessId]/assistant/channels/_lib/channels";
import { useBusinessFormat } from "@/components/business/BusinessContext";
import { IconCheckCircle, IconExternal } from "@/components/icons";
import { Alert, Button, Spinner, buttonClasses } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { QrImage } from "../QrImage";

export function TelegramLinkPanel({
  link,
  name,
  isLinked,
  onCancel,
}: {
  link: Schema<"TelegramLinkView">;
  name: string;
  isLinked: boolean;
  onCancel: () => void;
}) {
  const { t } = useI18n();
  const format = useBusinessFormat();

  if (isLinked) {
    return (
      <p role="status" className="flex items-center gap-2 rounded-2xl border border-success/40 bg-success-soft/60 p-4 text-sm font-medium text-ink">
        <IconCheckCircle className="size-5 shrink-0 text-success" aria-hidden />
        <span dir="auto">{t("tunnelTeam.people.telegramLinked", { name })}</span>
      </p>
    );
  }

  if (!link.deep_link && !link.bot_username) {
    return (
      <Alert
        tone="warning"
        action={
          <Button variant="ghost" size="sm" onClick={onCancel}>
            {t("common.cancel")}
          </Button>
        }
      >
        {t("tunnelTeam.people.telegramUnavailable")}
      </Alert>
    );
  }

  return (
    <div className="space-y-4 rounded-2xl border border-accent/30 bg-surface/90 p-4 backdrop-blur-sm sm:p-5">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-start">
        {link.deep_link ? (
          <QrImage value={link.deep_link} label={t("tunnelTeam.people.telegramTitle")} className="mx-auto size-40 shrink-0 sm:mx-0" />
        ) : null}
        <div className="min-w-0 flex-1 space-y-3">
          <h3 className="text-base font-semibold text-ink">{t("tunnelTeam.people.telegramTitle")}</h3>
          <p className="text-sm text-ink-muted">{t("tunnelTeam.people.telegramText")}</p>
          {link.deep_link ? (
            <a href={link.deep_link} target="_blank" rel="noopener noreferrer" className={buttonClasses({ size: "md" })}>
              <IconExternal className="size-4" aria-hidden />
              <span>{t("tunnelTeam.people.telegramOpen")}</span>
            </a>
          ) : null}
          <p className="text-sm text-ink-muted">
            {t("tunnelTeam.people.telegramCode", { code: formatLinkCode(link.code) })}
            {link.bot_username ? (
              <span className="ms-1 font-medium text-ink" dir="ltr">
                @{link.bot_username}
              </span>
            ) : null}
          </p>
          <p className="text-xs text-ink-subtle">{t("tunnelTeam.people.telegramExpires", { time: format.dateTime(link.expires_at) })}</p>
        </div>
      </div>
      <div className="flex items-center justify-between gap-3 border-t border-line pt-3">
        <p role="status" className="flex items-center gap-2 text-sm text-ink-muted">
          <Spinner size="sm" />
          {t("tunnelTeam.people.telegramWaiting")}
        </p>
        <Button variant="ghost" size="sm" onClick={onCancel}>
          {t("common.cancel")}
        </Button>
      </div>
    </div>
  );
}
