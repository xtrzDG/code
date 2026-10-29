"use client";

/**
 * A Telegram bot in three steps: open @BotFather, make a bot, paste its
 * token. Folded until the owner asks for it; a connected bot shows its name.
 */

import { useState, type FormEvent } from "react";

import type { Schema } from "@/api/types";
import { accountLabel } from "@/app/b/[businessId]/assistant/channels/_lib/channels";
import type { ConnectFieldError } from "@/app/b/[businessId]/assistant/channels/_lib/connectForm";
import { IconCheckCircle, IconExternal, IconTelegram } from "@/components/icons";
import { Button, Field, Input, buttonClasses } from "@/components/ui";
import { useI18n } from "@/i18n/client";

const BOT_FATHER = "https://t.me/BotFather";

export function TelegramBotCard({
  channel,
  token,
  onToken,
  error,
  isConnecting,
  onConnect,
}: {
  channel: Schema<"ChannelView"> | undefined;
  token: string;
  onToken: (token: string) => void;
  error: ConnectFieldError | null;
  isConnecting: boolean;
  onConnect: () => void;
}) {
  const { t } = useI18n();
  const [isOpen, setOpen] = useState(false);
  const bot = channel ? accountLabel("telegram", channel.account_id) : null;

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onConnect();
  };

  return (
    <section aria-labelledby="tunnel-telegram" className="rounded-2xl border border-line bg-surface/85 p-5 backdrop-blur-sm">
      <div className="flex items-start gap-3">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent" aria-hidden>
          <IconTelegram className="size-5" />
        </span>
        <div className="min-w-0 flex-1">
          <h2 id="tunnel-telegram" className="text-base font-semibold text-ink">
            {t("tunnelTeam.channels.telegram.title")}
          </h2>
          <p className="mt-1 text-sm text-ink-muted">{t("tunnelTeam.channels.telegram.text")}</p>
        </div>
        {!channel && !isOpen ? (
          <Button variant="secondary" size="sm" aria-expanded={false} onClick={() => setOpen(true)}>
            {t("tunnelTeam.channels.telegram.start")}
          </Button>
        ) : null}
      </div>

      {channel ? (
        <p role="status" className="mt-4 flex items-center gap-2 text-sm font-medium text-ink">
          <IconCheckCircle className="size-5 text-success" aria-hidden />
          <span dir="ltr">{bot ? t("tunnelTeam.channels.telegram.connected", { bot: bot.replace(/^@/, "") }) : t("tunnelTeam.channels.telegram.connectedNoName")}</span>
        </p>
      ) : isOpen ? (
        <div className="mt-5 space-y-4">
          <p className="text-sm font-medium text-ink">{t("tunnelTeam.channels.telegram.steps")}</p>
          <ol className="space-y-2 text-sm text-ink-muted">
            {(["step1", "step2", "step3"] as const).map((step, index) => (
              <li key={step} className="flex gap-3">
                <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-accent-soft text-xs font-semibold text-accent" aria-hidden>
                  {index + 1}
                </span>
                <span className="pt-0.5">{t(`tunnelTeam.channels.telegram.${step}`)}</span>
              </li>
            ))}
          </ol>
          <a href={BOT_FATHER} target="_blank" rel="noopener noreferrer" className={buttonClasses({ variant: "secondary", size: "sm" })}>
            <IconExternal className="size-4" aria-hidden />
            <span>{t("tunnelTeam.channels.telegram.openBotFather")}</span>
          </a>
          <form onSubmit={submit} noValidate data-enter="own" className="flex flex-col gap-3 sm:flex-row sm:items-start">
            <Field
              label={t("tunnelTeam.channels.telegram.token")}
              error={error ? t(error === "required" ? "tunnelTeam.channels.telegram.tokenRequired" : `channels.fieldErrors.${error}`) : undefined}
              className="min-w-0 flex-1"
            >
              {(control) => (
                <Input
                  {...control}
                  value={token}
                  dir="ltr"
                  autoComplete="off"
                  spellCheck={false}
                  placeholder={t("tunnelTeam.channels.telegram.tokenPlaceholder")}
                  onChange={(event) => onToken(event.target.value)}
                />
              )}
            </Field>
            <Button type="submit" isLoading={isConnecting} loadingText={t("tunnelTeam.channels.telegram.connecting")} className="sm:mt-7">
              {t("tunnelTeam.channels.telegram.connect")}
            </Button>
          </form>
        </div>
      ) : null}
    </section>
  );
}
