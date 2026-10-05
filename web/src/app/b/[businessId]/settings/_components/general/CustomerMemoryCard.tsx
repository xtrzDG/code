"use client";

import { useId } from "react";

import { Switch } from "@/components/content/Switch";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconCalendar, IconChat, IconClock } from "@/components/icons";
import { Card, ErrorState, SkeletonCard, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

import {
  canShareNotes,
  memoryBody,
  memoryChangeText,
  memorySwitches,
  type MemorySwitches,
} from "../../_lib/customerMemory";
import { useAssistantSettings } from "../../_lib/useAssistantSettings";

const REMEMBERED: ReadonlyArray<{ key: MessageKey; Icon: typeof IconClock }> = [
  { key: "customerMemory.remembers.visits", Icon: IconClock },
  { key: "customerMemory.remembers.summaries", Icon: IconChat },
  { key: "customerMemory.remembers.bookings", Icon: IconCalendar },
];

/**
 * Whether the assistant remembers returning customers (their visits,
 * summaries of earlier conversations, bookings to come and open requests)
 * and whether the team's notes reach that memory. Each switch saves at
 * once; staff see the settings, owners change them.
 */
export function CustomerMemoryCard() {
  const { t } = useI18n();
  const { settings } = useAssistantSettings();
  return (
    <Card title={t("customerMemory.title")} description={t("customerMemory.description")} data-testid="customer-memory">
      {settings.data ? (
        <MemorySwitchesForm switches={memorySwitches(settings.data)} />
      ) : settings.error ? (
        <ErrorState error={settings.error} onRetry={settings.reload} className="py-4" />
      ) : (
        <SkeletonCard lines={3} />
      )}
    </Card>
  );
}

function MemorySwitchesForm({ switches }: { switches: MemorySwitches }) {
  const { t } = useI18n();
  const toast = useToast();
  const { isOwner } = useBusiness();
  const { settings, save } = useAssistantSettings();
  const rememberHint = useId();
  const notesHint = useId();

  const change = async (update: Partial<MemorySwitches>) => {
    const result = await save.run(memoryBody(switches, update));
    if (result.ok) {
      settings.setData(result.data);
      const text = memoryChangeText(switches, memorySwitches(result.data));
      if (text !== null) {
        toast.success(t(text));
      }
    }
  };

  return (
    <div className="space-y-5">
      <SwitchRow
        label={t("customerMemory.remember.label")}
        hint={t("customerMemory.remember.hint")}
        hintId={rememberHint}
        checked={switches.remembersCustomers}
        disabled={!isOwner || save.isPending}
        onChange={(remembersCustomers) => void change({ remembersCustomers })}
      />
      <SwitchRow
        label={t("customerMemory.notes.label")}
        hint={switches.remembersCustomers ? t("customerMemory.notes.hint") : t("customerMemory.notes.needsMemory")}
        hintId={notesHint}
        checked={switches.remembersCustomers && switches.sharesTeamNotes}
        disabled={!canShareNotes(switches, isOwner) || save.isPending}
        onChange={(sharesTeamNotes) => void change({ sharesTeamNotes })}
      />
      <div className="rounded-xl bg-surface-muted px-4 py-3">
        <p className="text-sm font-medium text-ink">{t("customerMemory.remembers.title")}</p>
        <ul className="mt-2 space-y-2">
          {REMEMBERED.map(({ key, Icon }) => (
            <li key={key} className="flex items-start gap-2.5 text-sm text-ink-muted">
              <Icon className="mt-0.5 size-4 shrink-0 text-accent" aria-hidden />
              <span className="min-w-0">{t(key)}</span>
            </li>
          ))}
        </ul>
      </div>
      <p className="text-sm text-ink-muted">{t("customerMemory.bookingsQuestion")}</p>
      <p className="text-xs text-ink-subtle">{t("customerMemory.privacy")}</p>
      {isOwner ? null : <p className="text-xs text-ink-subtle">{t("customerMemory.ownerOnly")}</p>}
    </div>
  );
}

function SwitchRow({
  label,
  hint,
  hintId,
  checked,
  disabled,
  onChange,
}: {
  label: string;
  hint: string;
  hintId: string;
  checked: boolean;
  disabled: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="min-w-0 space-y-1">
        <p className="text-sm font-medium text-ink">{label}</p>
        <p id={hintId} className="text-sm text-ink-muted">
          {hint}
        </p>
      </div>
      <Switch checked={checked} onChange={onChange} label={label} describedBy={hintId} disabled={disabled} />
    </div>
  );
}
