"use client";

/**
 * The filters of the inbox: the channel on every view; on "All" also the
 * status, the period and test conversations (the whole history). Inline
 * under the search on large screens, in the Filters sheet on phones.
 */

import { useId, type ReactNode } from "react";

import { IncludeTestToggle } from "@/components/insights/common";
import {
  CHANNEL_LABELS,
  CONVERSATION_STATUS,
  CUSTOMER_CHANNELS,
} from "@/components/insights/labels";
import type {
  ChannelKind,
  ConversationStatus,
} from "@/components/insights/types";
import { Field, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import {
  CONVERSATION_PERIODS,
  type ConversationPeriod,
} from "../../_lib/conversationModel";
import type { InboxFilters } from "../../_lib/inboxModel";

export function InboxFilterFields({
  filters,
  onChange,
  layout,
}: {
  filters: InboxFilters;
  onChange: (filters: InboxFilters) => void;
  /** "inline": compact selects without visible labels; "sheet": labelled fields under each other. */
  layout: "inline" | "sheet";
}) {
  const { t } = useI18n();
  const id = useId();
  const isAll = filters.view === "all";
  const channels: ChannelKind[] =
    isAll && filters.includeTest
      ? [...CUSTOMER_CHANNELS, "owner_test"]
      : [...CUSTOMER_CHANNELS];
  const isSheet = layout === "sheet";

  // A control gets the id its label points to: the Field's in the sheet, ours inline.
  const field = (
    key: string,
    label: string,
    control: (controlId: string) => ReactNode,
  ) =>
    isSheet ? (
      <Field key={key} label={label}>
        {({ id: controlId }) => control(controlId)}
      </Field>
    ) : (
      <div key={key}>
        <label htmlFor={`${id}-${key}`} className="sr-only">
          {label}
        </label>
        {control(`${id}-${key}`)}
      </div>
    );

  return (
    <div className={cn(isSheet ? "space-y-4" : "grid grid-cols-2 gap-2")}>
      {field("channel", t("conversations.channel"), (controlId) => (
        <Select
          id={controlId}
          value={filters.channel ?? ""}
          onChange={(event) =>
            onChange({
              ...filters,
              channel: (event.target.value || null) as ChannelKind | null,
            })
          }
        >
          <option value="">{t("conversations.allChannels")}</option>
          {channels.map((channel) => (
            <option key={channel} value={channel}>
              {t(CHANNEL_LABELS[channel])}
            </option>
          ))}
        </Select>
      ))}
      {isAll ? (
        <>
          {field("status", t("conversations.statusFilter"), (controlId) => (
            <Select
              id={controlId}
              value={filters.status ?? ""}
              onChange={(event) =>
                onChange({
                  ...filters,
                  status: (event.target.value ||
                    null) as ConversationStatus | null,
                })
              }
            >
              <option value="">{t("conversations.allStatuses")}</option>
              {(Object.keys(CONVERSATION_STATUS) as ConversationStatus[]).map(
                (status) => (
                  <option key={status} value={status}>
                    {t(CONVERSATION_STATUS[status].label)}
                  </option>
                ),
              )}
            </Select>
          ))}
          {field("period", t("conversations.period"), (controlId) => (
            <Select
              id={controlId}
              value={filters.period}
              onChange={(event) =>
                onChange({
                  ...filters,
                  period: event.target.value as ConversationPeriod,
                })
              }
            >
              {CONVERSATION_PERIODS.map((period) => (
                <option key={period} value={period}>
                  {t(`conversations.periods.${period}`)}
                </option>
              ))}
            </Select>
          ))}
          <div className={cn("flex items-center", isSheet && "pt-1")}>
            <IncludeTestToggle
              compact={!isSheet}
              checked={filters.includeTest}
              onChange={(includeTest) =>
                onChange({
                  ...filters,
                  includeTest,
                  channel:
                    !includeTest && filters.channel === "owner_test"
                      ? null
                      : filters.channel,
                })
              }
            />
          </div>
        </>
      ) : null}
    </div>
  );
}
