"use client";

/**
 * The command palette: one text box over a list of where to go. With
 * nothing typed it offers the pages of the navigation; typing narrows
 * them and, inside a business, searches its customers, conversations and
 * bookings (two characters or more). Fully keyboard-usable: the focus
 * stays in the text box (a combobox), ↑/↓/Home/End move the highlight,
 * Enter opens it, Escape closes the palette and gives the focus back.
 * A pointer works too. The count of results is announced politely.
 */

import { useRouter } from "next/navigation";
import { useEffect, useId, useMemo, useState, type KeyboardEvent } from "react";

import { IconSearch } from "@/components/icons";
import { useModalDialog } from "@/components/ui/useModalDialog";
import { useI18n } from "@/i18n/client";
import { matchNavigation, movedIndex, navigationEntries, orderedEntries, type PaletteEntry, type PaletteNavLink } from "@/lib/commandPalette";

import { CommandPaletteResults, optionId } from "./CommandPaletteResults";
import { useCommandPaletteSearch, type PaletteSearchScope } from "./CommandPaletteSearch";

const MOVE_KEYS = new Set(["ArrowDown", "ArrowUp", "Home", "End"]);

export function CommandPalette({
  open,
  onClose,
  links,
  searchScope,
}: {
  open: boolean;
  onClose: () => void;
  links: readonly PaletteNavLink[];
  /** Where it searches customers, conversations and bookings; null: pages only. */
  searchScope: PaletteSearchScope | null;
}) {
  const { t, tp } = useI18n();
  const router = useRouter();
  const dialog = useModalDialog(open, onClose);
  const titleId = useId();
  const listboxId = useId();
  const statusId = useId();
  const [text, setText] = useState("");
  const [active, setActive] = useState(0);
  const [wasOpen, setWasOpen] = useState(open);

  // Every opening starts afresh.
  if (wasOpen !== open) {
    setWasOpen(open);
    if (open) {
      setText("");
      setActive(0);
    }
  }

  const pages = useMemo(() => navigationEntries(links), [links]);
  const search = useCommandPaletteSearch(searchScope, text);
  const entries = orderedEntries({ navigation: matchNavigation(pages, text), ...search.groups });
  const activeIndex = entries.length === 0 ? -1 : Math.min(active, entries.length - 1);

  // The highlighted option stays in sight as the arrows move it.
  useEffect(() => {
    if (open && activeIndex >= 0) {
      document.getElementById(optionId(listboxId, activeIndex))?.scrollIntoView({ block: "nearest" });
    }
  }, [open, activeIndex, listboxId]);

  const go = (entry: PaletteEntry | undefined) => {
    if (!entry) {
      return;
    }
    onClose();
    router.push(entry.href);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (MOVE_KEYS.has(event.key)) {
      event.preventDefault();
      setActive(movedIndex(activeIndex, entries.length, event.key));
    } else if (event.key === "Enter") {
      event.preventDefault();
      go(entries[activeIndex]);
    }
  };

  const status = search.isSearching
    ? t("palette.searching")
    : entries.length === 0
      ? t("palette.noResults", { text: text.trim() })
      : tp("palette.resultCount", entries.length);

  return (
    <dialog
      {...dialog}
      data-motion="modal"
      aria-labelledby={titleId}
      className="mx-auto mt-[10dvh] mb-auto w-[calc(100%-2rem)] max-w-xl overflow-hidden rounded-2xl border border-line bg-surface p-0 text-ink shadow-2xl"
    >
      <div className="flex max-h-[min(36rem,80dvh)] flex-col">
        <h2 id={titleId} className="sr-only">
          {t("palette.title")}
        </h2>
        <div className="flex shrink-0 items-center gap-3 border-b border-line px-4 focus-within:shadow-[inset_0_-2px_0_var(--focus)]">
          <IconSearch className="size-5 shrink-0 text-ink-subtle" aria-hidden />
          <input
            type="text"
            role="combobox"
            aria-expanded={entries.length > 0}
            aria-controls={listboxId}
            aria-activedescendant={activeIndex >= 0 ? optionId(listboxId, activeIndex) : undefined}
            aria-autocomplete="list"
            aria-describedby={statusId}
            aria-label={t("palette.placeholder")}
            placeholder={t("palette.placeholder")}
            value={text}
            dir="auto"
            maxLength={100}
            autoComplete="off"
            spellCheck={false}
            onChange={(event) => {
              setText(event.target.value);
              setActive(0);
            }}
            onKeyDown={onKeyDown}
            className="h-14 min-w-0 flex-1 bg-transparent text-base text-ink placeholder:text-ink-subtle outline-none!"
          />
          <kbd className="hidden shrink-0 rounded-md border border-line px-1.5 py-0.5 font-mono text-[11px] text-ink-subtle sm:inline">Esc</kbd>
        </div>
        {open ? (
          <CommandPaletteResults
            listboxId={listboxId}
            entries={entries}
            activeIndex={activeIndex}
            onHighlight={setActive}
            onOpen={go}
          />
        ) : null}
        <div className="shrink-0 space-y-1 border-t border-line px-4 py-2.5 text-xs text-ink-muted">
          <p id={statusId} role="status" aria-live="polite">
            {status}
          </p>
          {search.error ? <p className="text-warning">{t("palette.searchFailed")}</p> : null}
          {searchScope && search.searched === null && text.trim() !== "" ? <p>{t("palette.typeMore")}</p> : null}
          <p className="hidden sm:block">{t("palette.keys")}</p>
        </div>
      </div>
    </dialog>
  );
}
