"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { formatRelative } from "@/components/insights/dates";
import { Alert, Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

import { channelHealth, type ChannelFix, type ChannelProblem } from "../_lib/channelHealth";
import type { ChannelView, ConnectableChannel } from "../_lib/channels";

const PROBLEM_TEXTS: Record<ChannelProblem, MessageKey> = {
  credential_rejected: "channelSetup.health.problems.credential_rejected",
  channel_disconnected: "channelSetup.health.problems.channel_disconnected",
  not_configured: "channelSetup.health.problems.not_configured",
  template_rejected: "channelSetup.health.problems.template_rejected",
  recipient_refused: "channelSetup.health.problems.recipient_refused",
  rate_limited: "channelSetup.health.problems.rate_limited",
  provider_unavailable: "channelSetup.health.problems.provider_unavailable",
  expired: "channelSetup.health.problems.expired",
  unknown: "channelSetup.health.problems.unknown",
  missing_public_address: "channelSetup.health.problems.missing_public_address",
};

const FIX_LABELS: Record<ChannelFix, MessageKey> = {
  reconnect: "channelSetup.health.fix.reconnect",
  templates: "channelSetup.health.fix.templates",
};

/** Within a week "5 minutes ago", "yesterday"; older ones as a date. */
const RELATIVE_DAYS = 7;

/**
 * A connected channel's health on its card: when the last customer message
 * came in and the last reply went out, and the current problem in plain
 * words with the button that fixes it (owners). What the platform said
 * stays one click away, for support.
 */
export function ChannelHealthPanel({
  kind,
  channel,
  name,
  canManage,
  onFix,
}: {
  kind: ConnectableChannel;
  channel: ChannelView | undefined;
  /** The channel's name in the interface language. */
  name: string;
  canManage: boolean;
  onFix: (fix: ChannelFix) => void;
}) {
  const { t, locale } = useI18n();
  const format = useBusinessFormat();
  const health = channelHealth(kind, channel);
  if (!health || !channel) {
    return null;
  }
  const when = (value: number) => formatRelative(value, locale, { maxDays: RELATIVE_DAYS }) ?? format.dateTime(value);

  return (
    <div className="mt-4 space-y-3">
      {health.activity ? (
        <ul aria-label={t("channelSetup.health.label", { channel: name })} className="space-y-1 text-sm text-ink-muted">
          <li className="flex items-center gap-2">
            <ActivityDot isActive={health.activity.lastInboundAt !== null} />
            {health.activity.lastInboundAt !== null
              ? t("channelSetup.health.lastInbound", { when: when(health.activity.lastInboundAt) })
              : t("channelSetup.health.noInbound")}
          </li>
          <li className="flex items-center gap-2">
            <ActivityDot isActive={health.activity.lastOutboundAt !== null} />
            {health.activity.lastOutboundAt !== null
              ? t("channelSetup.health.lastOutbound", { when: when(health.activity.lastOutboundAt) })
              : t("channelSetup.health.noOutbound")}
          </li>
        </ul>
      ) : null}

      {health.problem ? (
        <Alert
          tone={health.tone}
          action={
            canManage && health.fix ? (
              <Button
                size="sm"
                variant={health.tone === "danger" ? "primary" : "secondary"}
                onClick={() => health.fix && onFix(health.fix)}
                aria-label={`${t(FIX_LABELS[health.fix])} — ${name}`}
              >
                {t(FIX_LABELS[health.fix])}
              </Button>
            ) : undefined
          }
        >
          <p className="text-ink">{t(PROBLEM_TEXTS[health.problem], { channel: name })}</p>
          {health.since !== null ? (
            <p className="mt-1 text-xs">{t("channelSetup.health.since", { when: when(health.since) })}</p>
          ) : null}
          {channel.last_error ? (
            <details className="mt-1 text-xs">
              <summary className="cursor-pointer select-none">{t("channelSetup.health.technical")}</summary>
              <p dir="auto" className="mt-1 font-mono break-words">
                {channel.last_error}
              </p>
            </details>
          ) : null}
        </Alert>
      ) : null}
    </div>
  );
}

function ActivityDot({ isActive }: { isActive: boolean }) {
  return <span aria-hidden className={isActive ? "size-1.5 shrink-0 rounded-full bg-success" : "size-1.5 shrink-0 rounded-full bg-line-strong"} />;
}
