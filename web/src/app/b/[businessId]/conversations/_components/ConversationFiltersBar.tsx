"use client";

import { useEffect, useId, useRef, useState } from "react";

import { IncludeTestToggle } from "@/components/insights/common";
import { CHANNEL_LABELS, CONVERSATION_STATUS, CUSTOMER_CHANNELS } from "@/components/insights/labels";
import type { ChannelKind, ConversationStatus } from "@/components/insights/types";
import { Input, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { CONVERSATION_PERIODS, type ConversationFilters, type ConversationPeriod } from "./conversationModel";

const SEARCH_DELAY_MS = 300;

export function ConversationFiltersBar({
  filters,
  onChange,
}: {
  filters: ConversationFilters;
  onChange: (filters: ConversationFilters) => void;
}) {
  const { t } = useI18n();
  const id = useId();
  // Typed text not yet applied; null shows the applied search.
  const [draft, setDraft] = useState<string | null>(null);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const typeSearch = (text: string) => {
    setDraft(text);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      onChange({ ...filters, search: text });
      setDraft(null);
    }, SEARCH_DELAY_MS);
  };

  const channels: ChannelKind[] = filters.includeTest ? [...CUSTOMER_CHANNELS, "owner_test"] : [...CUSTOMER_CHANNELS];

  return (
    <div className="space-y-2">
      <div>
        <label htmlFor={`${id}-search`} className="sr-only">
          {t("conversations.search")}
        </label>
        <Input
          id={`${id}-search`}
          type="search"
          value={draft ?? filters.search}
          onChange={(event) => typeSearch(event.target.value)}
          placeholder={t("conversations.searchPlaceholder")}
          autoComplete="off"
          enterKeyHint="search"
        />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label htmlFor={`${id}-channel`} className="sr-only">
            {t("conversations.channel")}
          </label>
          <Select
            id={`${id}-channel`}
            value={filters.channel ?? ""}
            onChange={(event) => onChange({ ...filters, channel: (event.target.value || null) as ChannelKind | null })}
          >
            <option value="">{t("conversations.allChannels")}</option>
            {channels.map((channel) => (
              <option key={channel} value={channel}>
                {t(CHANNEL_LABELS[channel])}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <label htmlFor={`${id}-status`} className="sr-only">
            {t("conversations.statusFilter")}
          </label>
          <Select
            id={`${id}-status`}
            value={filters.status ?? ""}
            onChange={(event) =>
              onChange({ ...filters, status: (event.target.value || null) as ConversationStatus | null })
            }
          >
            <option value="">{t("conversations.allStatuses")}</option>
            {(Object.keys(CONVERSATION_STATUS) as ConversationStatus[]).map((status) => (
              <option key={status} value={status}>
                {t(CONVERSATION_STATUS[status].label)}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <label htmlFor={`${id}-period`} className="sr-only">
            {t("conversations.period")}
          </label>
          <Select
            id={`${id}-period`}
            value={filters.period}
            onChange={(event) => onChange({ ...filters, period: event.target.value as ConversationPeriod })}
          >
            {CONVERSATION_PERIODS.map((period) => (
              <option key={period} value={period}>
                {t(`conversations.periods.${period}`)}
              </option>
            ))}
          </Select>
        </div>
        <div className="flex items-center">
          <IncludeTestToggle
            compact
            checked={filters.includeTest}
            onChange={(includeTest) =>
              onChange({
                ...filters,
                includeTest,
                channel: !includeTest && filters.channel === "owner_test" ? null : filters.channel,
              })
            }
          />
        </div>
      </div>
    </div>
  );
}
