"use client";

import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { Alert, Badge, Button, ButtonLink } from "@/components/ui";
import { DANGER_GHOST } from "@/components/workspace/styles";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { businessPath } from "@/lib/navigation";

import {
  CHANNEL_STATE_TONES,
  accountLabel,
  channelState,
  isChannelOn,
  type ChannelView,
  type ConnectableChannel,
} from "../_lib/channels";
import { CHANNEL_ACCOUNT_LABELS, CHANNEL_BLURBS, CHANNEL_ICONS, CHANNEL_NAMES, CHANNEL_STATE_LABELS } from "./channelMeta";

/** One customer channel: status, account, and connect / disconnect for the owner. */
export function ChannelCard({
  kind,
  channel,
  isInPlan,
  canManage,
  isBusy,
  onConnect,
  onDisconnect,
}: {
  kind: ConnectableChannel;
  channel: ChannelView | undefined;
  isInPlan: boolean;
  canManage: boolean;
  /** A connect or disconnect of this channel is running. */
  isBusy: boolean;
  onConnect: (kind: ConnectableChannel) => void;
  onDisconnect: (kind: ConnectableChannel) => void;
}) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const format = useBusinessFormat();
  const state = channelState(channel);
  const isOn = isChannelOn(channel);
  const Icon = CHANNEL_ICONS[kind];
  const name = t(CHANNEL_NAMES[kind]);
  const account = accountLabel(kind, channel?.account_id);
  const accountLabelKey = CHANNEL_ACCOUNT_LABELS[kind];
  const headingId = `channel-${kind}-title`;

  const connectLabel = isOn ? t("channels.reconnect") : kind === "web_chat" ? t("channels.turnOn") : t("channels.connect");

  return (
    <section
      aria-labelledby={headingId}
      className={cn(
        "flex h-full flex-col rounded-2xl border bg-surface p-5 shadow-sm",
        state === "error" ? "border-danger/40" : "border-line",
      )}
    >
      <div className="flex items-start gap-3">
        <span
          className={cn(
            "flex size-10 shrink-0 items-center justify-center rounded-xl",
            isOn ? "bg-accent-soft text-accent" : "bg-surface-muted text-ink-muted",
          )}
          aria-hidden
        >
          <Icon className="size-5" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <h3 id={headingId} className="text-base font-semibold text-ink">
              {name}
            </h3>
            <Badge tone={CHANNEL_STATE_TONES[state]}>{t(CHANNEL_STATE_LABELS[state])}</Badge>
            {!isInPlan ? <Badge tone="warning">{t("channels.notInPlan")}</Badge> : null}
          </div>
          <p className="mt-1 text-sm text-ink-muted">{t(CHANNEL_BLURBS[kind])}</p>
        </div>
      </div>

      {isOn && account && accountLabelKey ? (
        <dl className="mt-4 flex flex-wrap gap-x-2 text-sm">
          <dt className="text-ink-subtle">{t(accountLabelKey)}:</dt>
          <dd className="font-medium break-all text-ink" dir="ltr">
            {account}
          </dd>
        </dl>
      ) : null}
      {channel ? (
        <p className={cn("text-xs text-ink-subtle", isOn && account ? "mt-1" : "mt-4")}>
          {t("channels.updatedAt", { date: format.dateTime(channel.updated_at) })}
        </p>
      ) : null}

      {state === "error" ? (
        <Alert tone="danger" title={t("channels.errorTitle")} className="mt-4">
          {channel?.last_error_at ? <p>{t("channels.errorSince", { date: format.dateTime(channel.last_error_at) })}</p> : null}
          <p>{t("channels.errorDescription")}</p>
          {channel?.last_error ? (
            <p className="mt-1 text-xs break-words">
              {t("channels.errorReason")}{" "}
              <span dir="auto" className="font-mono">
                {channel.last_error}
              </span>
            </p>
          ) : null}
          <p className="mt-1 text-xs">{t("channels.errorHeals")}</p>
        </Alert>
      ) : null}
      {state === "pending" ? (
        <Alert tone="info" className="mt-4">
          {t("channels.pendingDescription")}
        </Alert>
      ) : null}
      {!isInPlan ? (
        <Alert tone="warning" className="mt-4">
          <p>{t("channels.notInPlanHint")}</p>
          <ButtonLink href={businessPath(business.id, "billing")} variant="secondary" size="sm" className="mt-3">
            {t("channels.openBilling")}
          </ButtonLink>
        </Alert>
      ) : null}

      {canManage ? (
        <div className="mt-auto flex flex-wrap gap-2 pt-5">
          <Button
            variant={isOn ? "secondary" : "primary"}
            size="sm"
            onClick={() => onConnect(kind)}
            isLoading={isBusy && !isOn}
            disabled={isBusy}
            aria-label={`${connectLabel} — ${name}`}
          >
            {connectLabel}
          </Button>
          {isOn ? (
            <Button
              variant="ghost"
              size="sm"
              className={DANGER_GHOST}
              onClick={() => onDisconnect(kind)}
              disabled={isBusy}
              aria-label={`${t("channels.disconnect")} — ${name}`}
            >
              {t("channels.disconnect")}
            </Button>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
