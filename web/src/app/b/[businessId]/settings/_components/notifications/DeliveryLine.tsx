"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { IconAlert } from "@/components/icons";
import { Badge } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { DELIVERY_LABELS, DELIVERY_TONES, type NotificationContact } from "../../_lib/notifications";
import { CHANNEL_LABELS } from "./contactTexts";

/**
 * How notifications reach a contact: a channel the platform cannot send by
 * (no provider configured), or the latest notification's state with its
 * time and, when it failed, the provider's reason.
 */
export function DeliveryLine({ status }: { status: NotificationContact }) {
  const { t } = useI18n();
  const format = useBusinessFormat();
  if (!status.provider_ready && !status.delivery) {
    return (
      <p className="flex flex-wrap items-center gap-2 text-sm text-ink-muted">
        <Badge tone="warning" icon={<IconAlert className="size-3.5" aria-hidden />}>
          {t("notifications.contacts.providerMissing")}
        </Badge>
        <span>{t("notifications.contacts.providerMissingHint", { channel: t(CHANNEL_LABELS[status.channel]) })}</span>
      </p>
    );
  }
  const delivery = status.delivery;
  if (!delivery) {
    return <p className="text-sm text-ink-subtle">{t("notifications.contacts.never")}</p>;
  }
  return (
    <div className="space-y-1">
      <p className="flex flex-wrap items-center gap-2 text-sm text-ink-muted">
        <Badge tone={DELIVERY_TONES[delivery.status]}>{t(DELIVERY_LABELS[delivery.status])}</Badge>
        <span>
          {delivery.delivered_at
            ? t("notifications.contacts.deliveredAt", { time: format.dateTime(delivery.delivered_at) })
            : t("notifications.contacts.attemptedAt", { time: format.dateTime(delivery.attempted_at) })}
        </span>
      </p>
      {delivery.last_error && delivery.status !== "delivered" ? (
        <p className="text-sm break-words text-danger">{delivery.last_error}</p>
      ) : null}
    </div>
  );
}
