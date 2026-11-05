"use client";

import { Badge } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { DEPOSIT_STATUS, type DepositStatus } from "./depositModel";

/** "Deposit · Awaiting payment": the chip of a booking whose deposit was asked. */
export function DepositBadge({ status }: { status: DepositStatus }) {
  const { t } = useI18n();
  const entry = DEPOSIT_STATUS[status];
  return (
    <Badge tone={entry.tone}>
      {t("deposits.chip")} · {t(entry.label)}
    </Badge>
  );
}
