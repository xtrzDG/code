"use client";

/**
 * The palette's list: one listbox of options in groups ("Go to",
 * customers, conversations, bookings). The highlighted option is the
 * input's active descendant, so the keyboard never leaves the text box;
 * a pointer highlights on hover and opens on click.
 */

import type { ComponentType } from "react";

import { IconCalendar, IconChat, IconChevronRight, IconUsers, type IconProps } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { PALETTE_GROUPS, type PaletteEntry, type PaletteGroup } from "@/lib/commandPalette";
import { cn } from "@/lib/cn";

const GROUP_LABELS: Record<PaletteGroup, MessageKey> = {
  navigation: "palette.groups.navigation",
  customers: "palette.groups.customers",
  conversations: "palette.groups.conversations",
  bookings: "palette.groups.bookings",
};

const GROUP_ICONS: Record<PaletteGroup, ComponentType<IconProps>> = {
  navigation: IconChevronRight,
  customers: IconUsers,
  conversations: IconChat,
  bookings: IconCalendar,
};

/** The id of an option's element (the input's aria-activedescendant). */
export function optionId(listboxId: string, index: number): string {
  return `${listboxId}-option-${index}`;
}

export function CommandPaletteResults({
  listboxId,
  entries,
  activeIndex,
  onHighlight,
  onOpen,
}: {
  listboxId: string;
  /** In the order of the groups (orderedEntries). */
  entries: readonly PaletteEntry[];
  activeIndex: number;
  onHighlight: (index: number) => void;
  onOpen: (entry: PaletteEntry) => void;
}) {
  const { t } = useI18n();

  return (
    <div id={listboxId} role="listbox" aria-label={t("palette.title")} className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-2 pb-2">
      {PALETTE_GROUPS.map((group) => {
        const members = entries.filter((entry) => entry.group === group);
        if (members.length === 0) {
          return null;
        }
        const headingId = `${listboxId}-${group}`;
        const Icon = GROUP_ICONS[group];
        return (
          <div key={group} role="group" aria-labelledby={headingId} className="pt-2">
            <div id={headingId} role="presentation" className="px-3 pt-1 pb-1.5 text-xs font-medium text-ink-subtle">
              {t(GROUP_LABELS[group])}
            </div>
            {members.map((entry) => {
              const position = entries.indexOf(entry);
              const isActive = position === activeIndex;
              return (
                <div
                  key={entry.id}
                  id={optionId(listboxId, position)}
                  role="option"
                  aria-selected={isActive}
                  // Keep the focus in the text box: the keyboard goes on from there.
                  onMouseDown={(event) => event.preventDefault()}
                  onMouseMove={() => onHighlight(position)}
                  onClick={() => onOpen(entry)}
                  className={cn(
                    "flex min-h-11 cursor-pointer items-center gap-3 rounded-xl px-3 py-2 text-sm",
                    isActive ? "bg-accent-soft text-accent-ink" : "text-ink",
                  )}
                >
                  <Icon className={cn("size-4 shrink-0", isActive ? "text-accent-ink" : "text-ink-subtle")} aria-hidden />
                  <span className="min-w-0 flex-1">
                    <span dir="auto" className="block truncate font-medium">
                      {entry.label}
                    </span>
                    {entry.detail ? (
                      <span dir="auto" className={cn("block truncate text-xs", isActive ? "text-accent-ink" : "text-ink-muted")}>
                        {entry.detail}
                      </span>
                    ) : null}
                  </span>
                </div>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}
