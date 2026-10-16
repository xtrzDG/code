"use client";

/**
 * The details and the team's notes of a conversation, out of the way of
 * the transcript: a sheet from the bottom on phones, a panel from the
 * side on laptops, and a column of its own beside the conversation on
 * wide screens. Two tabs: Details and Notes.
 */

import { useId, type ReactNode } from "react";

import { Sheet } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

export type PanelTab = "details" | "notes";

function PanelTabs({
  value,
  noteCount,
  onChange,
}: {
  value: PanelTab;
  noteCount: number | null;
  onChange: (tab: PanelTab) => void;
}) {
  const { t, tp } = useI18n();
  const name = useId();
  const tabs: { tab: PanelTab; label: string }[] = [
    { tab: "details", label: t("inboxCard.openDetails") },
    { tab: "notes", label: noteCount ? tp("inboxCard.openNotesCount", noteCount) : t("inboxCard.openNotes") },
  ];
  return (
    <fieldset className="mb-4">
      <legend className="sr-only">{t("inboxCard.panelTabs")}</legend>
      <div className="flex gap-1 rounded-xl border border-line bg-surface-muted p-1">
        {tabs.map(({ tab, label }) => (
          <label
            key={tab}
            className={cn(
              "flex min-h-9 flex-1 cursor-pointer items-center justify-center rounded-lg px-3 text-sm font-medium transition-colors",
              "has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-focus",
              value === tab ? "bg-surface text-ink shadow-sm" : "text-ink-muted hover:text-ink",
            )}
          >
            <input type="radio" name={name} className="sr-only" checked={value === tab} onChange={() => onChange(tab)} />
            {label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export function ConversationPanel({
  tab,
  onTab,
  isOpen,
  onClose,
  isInline,
  noteCount,
  details,
  notes,
}: {
  tab: PanelTab;
  onTab: (tab: PanelTab) => void;
  /** Shown as a sheet (ignored inline, where it is always there). */
  isOpen: boolean;
  onClose: () => void;
  /** A column beside the conversation (wide screens). */
  isInline: boolean;
  noteCount: number | null;
  details: ReactNode;
  notes: ReactNode;
}) {
  const { t } = useI18n();
  const body = (
    <>
      <PanelTabs value={tab} noteCount={noteCount} onChange={onTab} />
      {tab === "details" ? details : notes}
    </>
  );

  if (isInline) {
    return (
      <aside aria-label={t("inboxCard.panelLabel")} className="min-h-0 overflow-y-auto rounded-2xl border border-line bg-canvas/40 p-4">
        {body}
      </aside>
    );
  }
  return (
    <Sheet open={isOpen} onClose={onClose} title={t("inboxCard.panelLabel")}>
      {body}
    </Sheet>
  );
}
