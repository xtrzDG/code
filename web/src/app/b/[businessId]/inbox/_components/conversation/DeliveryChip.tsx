"use client";

/**
 * How a staff reply travels to the customer, under its bubble: sending,
 * not delivered yet and tried again (with why, and when the next try is),
 * delivered, or not delivered (with why). Read from the reply's outbox
 * message (`MessageView.delivery`); the card reloads on every attempt.
 */

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { IconAlert, IconCheck, IconClock, IconRefresh } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { describeDelivery, type MessageDelivery } from "../../_lib/staffDeliveries";

const LOOKS: Record<MessageDelivery["state"], { chip: string; Icon: typeof IconCheck }> = {
  sending: { chip: "bg-surface-muted text-ink-muted", Icon: IconClock },
  retrying: { chip: "bg-warning-soft text-warning", Icon: IconRefresh },
  delivered: { chip: "text-ink-subtle", Icon: IconCheck },
  failed: { chip: "bg-danger-soft text-danger", Icon: IconAlert },
};

export function DeliveryChip({ delivery, className }: { delivery: MessageDelivery; className?: string }) {
  const { t } = useI18n();
  const format = useBusinessFormat();
  const { chip, Icon } = LOOKS[delivery.state];
  const { state, reason, nextAttemptAt } = describeDelivery(delivery);
  const details: string[] = [];
  if (reason) {
    details.push(t(reason));
  }
  if (nextAttemptAt !== null) {
    details.push(t("messageDelivery.nextAttempt", { time: format.time(nextAttemptAt) }));
  }

  return (
    <p className={cn("flex justify-end", className)} data-delivery-state={delivery.state}>
      <span className={cn("inline-flex max-w-full items-start gap-1 rounded-2xl px-2.5 py-0.5 text-xs", chip)}>
        <Icon className={cn("mt-0.5 size-3.5 shrink-0", delivery.state === "sending" && "motion-safe:animate-pulse")} aria-hidden />
        <span className="min-w-0 text-left break-words">
          <span className="sr-only">{`${t("messageDelivery.label")}: `}</span>
          <span className="font-medium">{t(state)}</span>
          {details.length > 0 ? <span>{`: ${details.join(", ")}`}</span> : null}
        </span>
      </span>
    </p>
  );
}
