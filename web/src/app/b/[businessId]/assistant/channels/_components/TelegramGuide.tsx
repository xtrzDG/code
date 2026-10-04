"use client";

import { useEffect, useState, type FormEvent, type ReactNode } from "react";

import { api } from "@/api/client";
import type { ErrorMessageOverrides } from "@/api/errors";
import { useMutation } from "@/api/useMutation";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconCheck, IconExternal } from "@/components/icons";
import { Button, Field, Input, Spinner, buttonClasses } from "@/components/ui";
import { InlineError } from "@/components/ui/InlineError";
import { CopyButton } from "@/components/workspace/CopyButton";
import { useI18n } from "@/i18n/client";

import type { ConnectChannelBody } from "../_lib/connectForm";
import { isBotToken } from "../_lib/connectForm";
import {
  alternativeBotUsername,
  botHandle,
  botInitial,
  BOTFATHER_URL,
  cleanBotToken,
  NEW_BOT_COMMAND,
  suggestBotUsername,
  tokenCheckProblem,
  type TelegramBotCheck,
  type TokenCheckProblem,
} from "../_lib/telegramSetup";

/** A pause after typing or pasting before the token goes to Telegram. */
const CHECK_DELAY_MS = 400;

type CheckState = { token: string; bot: TelegramBotCheck } | { token: string; problem: TokenCheckProblem };

/**
 * Telegram in four steps: open @BotFather, send /newbot, give it the name
 * and the suggested username, paste the key it sends. The key is checked
 * with Telegram as soon as it is pasted (nothing is saved): the owner sees
 * the bot's name and photo before connecting it.
 */
export function TelegramGuide({
  isPending,
  error,
  errorOverrides,
  onClose,
  onSubmit,
}: {
  isPending: boolean;
  error: unknown;
  errorOverrides?: ErrorMessageOverrides;
  onClose: () => void;
  onSubmit: (kind: "telegram", body: ConnectChannelBody) => Promise<boolean>;
}) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const [tokenText, setTokenText] = useState("");
  const [checked, setChecked] = useState<CheckState | null>(null);
  const token = cleanBotToken(tokenText);
  const isShaped = isBotToken(token);

  const validate = useMutation(
    (botToken: string) =>
      api.POST("/v1/businesses/{business_id}/channels/telegram/validate-token", {
        params: { path: { business_id: business.id } },
        body: { bot_token: botToken },
      }),
    { errorToast: false },
  );
  const runCheck = validate.run;

  useEffect(() => {
    if (!isShaped) {
      return;
    }
    const timer = window.setTimeout(() => {
      void runCheck(token).then((result) =>
        setChecked(result.ok ? { token, bot: result.data } : { token, problem: tokenCheckProblem(result.error) }),
      );
    }, CHECK_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [isShaped, runCheck, token]);

  // Only the answer about the key in the field counts.
  const current = checked?.token === token ? checked : null;
  const bot = current && "bot" in current ? current.bot : null;
  const problem: TokenCheckProblem | null =
    current && "problem" in current ? current.problem : token.length > 0 && !isShaped ? "format" : null;
  const isChecking = isShaped && current === null;
  const canConnect = isShaped && problem !== "rejected" && problem !== "format";

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canConnect) {
      return;
    }
    if (await onSubmit("telegram", { bot_token: token })) {
      // The key never stays in memory longer than needed.
      setTokenText("");
      setChecked(null);
    }
  };

  const username = suggestBotUsername(business.name);
  return (
    <form onSubmit={(event) => void submit(event)} noValidate className="space-y-5">
      <p className="text-sm text-ink-muted">{t("channelSetup.telegram.intro")}</p>
      <ol className="space-y-4">
        <Step number={1} title={t("channelSetup.telegram.step1")}>
          <a href={BOTFATHER_URL} target="_blank" rel="noopener noreferrer" className={buttonClasses({ variant: "secondary", size: "sm" })}>
            <IconExternal aria-hidden className="size-4" />
            {t("channelSetup.telegram.openBotFather")}
          </a>
        </Step>
        <Step number={2} title={t("channelSetup.telegram.step2")}>
          <CopyRow value={NEW_BOT_COMMAND} />
        </Step>
        <Step number={3} title={t("channelSetup.telegram.step3")}>
          <CopyRow label={t("channelSetup.telegram.nameLabel")} value={business.name} />
          <CopyRow label={t("channelSetup.telegram.usernameLabel")} value={username} />
          <p className="text-xs text-ink-subtle">
            {t("channelSetup.telegram.usernameHint", { example: alternativeBotUsername(business.name) })}
          </p>
        </Step>
        <Step number={4} title={t("channelSetup.telegram.step4")}>
          <Field
            label={t("channelSetup.telegram.tokenLabel")}
            hint={t("channelSetup.telegram.tokenHint")}
            error={problem === "format" || problem === "rejected" ? t(`channelSetup.telegram.${problem}`) : undefined}
            required
          >
            {(control) => (
              <Input
                {...control}
                type="password"
                autoComplete="off"
                autoCapitalize="off"
                spellCheck={false}
                dir="ltr"
                placeholder="123456789:AAH…"
                value={tokenText}
                onChange={(event) => setTokenText(event.target.value)}
              />
            )}
          </Field>
          <div aria-live="polite" className="min-h-6">
            {isChecking ? (
              <p className="flex items-center gap-2 text-sm text-ink-muted">
                <Spinner size="sm" />
                {t("channelSetup.telegram.checking")}
              </p>
            ) : bot ? (
              <BotCard bot={bot} />
            ) : problem === "unavailable" ? (
              <p className="text-sm text-ink-muted">{t("channelSetup.telegram.unavailable")}</p>
            ) : null}
          </div>
        </Step>
      </ol>

      <InlineError error={error} overrides={errorOverrides} />
      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <Button variant="secondary" onClick={onClose} disabled={isPending}>
          {t("common.cancel")}
        </Button>
        <Button type="submit" isLoading={isPending} loadingText={t("channels.connecting")} disabled={!canConnect}>
          {bot ? t("channelSetup.telegram.connectBot", { bot: botHandle(bot) }) : t("channelSetup.telegram.connect")}
        </Button>
      </div>
    </form>
  );
}

function Step({ number, title, children }: { number: number; title: string; children: ReactNode }) {
  return (
    <li className="flex gap-3">
      <span aria-hidden className="flex size-6 shrink-0 items-center justify-center rounded-full bg-accent-soft text-xs font-semibold text-accent">
        {number}
      </span>
      <div className="min-w-0 flex-1 space-y-2">
        <p className="text-sm font-medium text-ink">{title}</p>
        {children}
      </div>
    </li>
  );
}

function CopyRow({ label, value }: { label?: string; value: string }) {
  return (
    <div className="flex items-center gap-2">
      {label ? <span className="w-28 shrink-0 text-xs text-ink-subtle">{label}</span> : null}
      <code dir="auto" className="min-w-0 flex-1 truncate rounded-lg bg-surface-muted px-3 py-1.5 font-mono text-sm text-ink">
        {value}
      </code>
      <CopyButton value={value} iconOnly />
    </div>
  );
}

function BotCard({ bot }: { bot: TelegramBotCheck }) {
  const { t } = useI18n();
  const handle = botHandle(bot);
  return (
    <div className="flex items-center gap-3 rounded-xl border border-success/30 bg-success-soft p-3">
      {bot.avatar_data_url ? (
        // A data: URL of a small photo the API fetched; next/image adds nothing here.
        // eslint-disable-next-line @next/next/no-img-element
        <img src={bot.avatar_data_url} alt={t("channelSetup.telegram.avatarAlt", { bot: handle })} className="size-12 shrink-0 rounded-full object-cover" />
      ) : (
        <span aria-hidden className="flex size-12 shrink-0 items-center justify-center rounded-full bg-accent-solid text-lg font-semibold text-on-accent">
          {botInitial(bot)}
        </span>
      )}
      <div className="min-w-0 flex-1">
        <p className="flex items-center gap-1.5 text-sm font-medium text-success">
          <IconCheck aria-hidden className="size-4" />
          {t("channelSetup.telegram.found")}
        </p>
        <p dir="auto" className="truncate text-base font-semibold text-ink">
          {bot.display_name ?? handle}
        </p>
        <p dir="ltr" className="truncate text-sm text-ink-muted">
          {handle}
        </p>
      </div>
    </div>
  );
}
