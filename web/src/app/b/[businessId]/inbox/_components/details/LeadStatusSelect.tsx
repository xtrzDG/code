"use client";

import { LEAD_STATUS, LEAD_STATUSES } from "@/components/insights/labels";
import type { LeadListItem, LeadStatus } from "@/components/insights/types";
import { Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";

/**
 * A lead's status as a select that moves it. It stays usable while the
 * move is saved (the list already shows it; a refusal puts it back).
 */
export function LeadStatusSelect({
  lead,
  isPending,
  onStatus,
  label,
}: {
  lead: LeadListItem;
  isPending: boolean;
  onStatus: (status: LeadStatus) => void;
  label: string;
}) {
  const { t } = useI18n();
  return (
    <Select
      aria-label={label}
      value={lead.status}
      aria-busy={isPending || undefined}
      onChange={(event) => onStatus(event.target.value as LeadStatus)}
      className="w-full sm:w-44"
    >
      {LEAD_STATUSES.map((status) => (
        <option key={status} value={status}>
          {t(LEAD_STATUS[status].label)}
        </option>
      ))}
    </Select>
  );
}
