"use client";

/**
 * Triage state of the inbox list: the keyboard cursor, the selection for a
 * bulk "Mark resolved", the shortcuts sheet, and the keys themselves
 * (lib inboxShortcuts.ts): j/k move the cursor (and the focus) through the
 * rows, Enter opens, e resolves the selection or the row under the cursor
 * (or the open conversation), a takes it, x selects it, / goes to the
 * search, ? opens the sheet, Escape clears the selection.
 */

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { InboxView } from "@/lib/navigation";

import type { InboxRow } from "./inboxModel";
import { shortcutOf, type InboxShortcut } from "./inboxShortcuts";
import { movedCursor, prunedSelection, selectionState, toggledAll, toggledSelection } from "./triage";
import type { InboxList } from "./useInboxList";
import { useTriageActions } from "./useTriageActions";

const NOTHING: ReadonlySet<string> = new Set();

function rowLink(id: string): HTMLAnchorElement | null {
  return document.querySelector<HTMLAnchorElement>(`[data-inbox-row="${CSS.escape(id)}"] a[href]`);
}

/** The list is on screen (on a phone with a conversation open it is not). */
function isListShown(): boolean {
  const list = document.querySelector<HTMLElement>("[data-inbox-list]");
  return list !== null && list.offsetParent !== null;
}

export function useInboxTriage({ view, list, openId }: { view: InboxView; list: InboxList; openId: string | null }) {
  const router = useRouter();
  const rows = useMemo(() => list.rows ?? [], [list.rows]);
  const actions = useTriageActions(view, list);
  const [cursorId, setCursorId] = useState<string | null>(null);
  // The selection belongs to the view it was made in.
  const [chosen, setChosen] = useState<{ view: InboxView; ids: ReadonlySet<string> }>({ view, ids: NOTHING });
  const [isSheetOpen, setSheetOpen] = useState(false);
  const [isResolving, setResolving] = useState(false);

  // Another view clears it; after a reload only rows still shown and still resolvable stay selected.
  const selection = useMemo(
    () => (chosen.view === view ? prunedSelection(chosen.ids, rows) : NOTHING),
    [chosen, view, rows],
  );
  const setSelection = (next: ReadonlySet<string> | ((selected: ReadonlySet<string>) => ReadonlySet<string>)) =>
    setChosen((current) => {
      const selected = current.view === view ? prunedSelection(current.ids, rows) : NOTHING;
      return { view, ids: typeof next === "function" ? next(selected) : next };
    });

  const rowById = useCallback((id: string | null) => rows.find((row) => row.id === id) ?? null, [rows]);
  const focusRow = (id: string | null) => {
    if (id !== null) {
      setCursorId(id);
      rowLink(id)?.focus();
    }
  };

  const resolveRows = async (targets: readonly InboxRow[], { thenFocus }: { thenFocus: string | null }) => {
    setResolving(true);
    await actions.resolve(targets);
    setResolving(false);
    setSelection(NOTHING);
    if (thenFocus !== null) {
      window.requestAnimationFrame(() => focusRow(thenFocus));
    }
  };

  const resolveSelected = () => void resolveRows(rows.filter((row) => selection.has(row.id)), { thenFocus: null });

  const resolveCurrent = (row: InboxRow) => {
    const after = movedCursor(rows, row.id, 1);
    void resolveRows([row], { thenFocus: after === row.id ? movedCursor(rows, row.id, -1) : after });
  };

  const handle = (shortcut: InboxShortcut): boolean => {
    const current = rowById(cursorId) ?? rowById(openId);
    switch (shortcut) {
      case "next":
      case "previous":
        if (!isListShown()) {
          return false;
        }
        focusRow(movedCursor(rows, cursorId ?? openId, shortcut === "next" ? 1 : -1));
        return true;
      case "open": {
        const target = rowById(cursorId);
        const href = target ? rowLink(target.id)?.getAttribute("href") : null;
        if (href) {
          router.push(href);
        }
        return Boolean(href);
      }
      case "resolve":
        if (selection.size > 0) {
          resolveSelected();
        } else if (current) {
          resolveCurrent(current);
        }
        return selection.size > 0 || current !== null;
      case "assign":
        if (current) {
          void actions.takeIt(current);
        }
        return current !== null;
      case "select":
        if (current) {
          setSelection((selected) => toggledSelection(selected, current));
        }
        return current !== null;
      case "search":
        document.querySelector<HTMLInputElement>("[data-inbox-search]")?.focus();
        return true;
      case "help":
        setSheetOpen(true);
        return true;
      case "clear":
        if (selection.size === 0) {
          return false;
        }
        setSelection(NOTHING);
        return true;
    }
  };

  // One listener for the page; it always calls the latest handler.
  const handler = useRef(handle);
  useEffect(() => {
    handler.current = handle;
  });
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target instanceof HTMLElement ? event.target : null;
      const shortcut = shortcutOf(
        event,
        target && { tagName: target.tagName, isContentEditable: target.isContentEditable, type: (target as HTMLInputElement).type },
        {
          isDialogOpen: document.querySelector("dialog[open]") !== null,
          onControl: target?.closest("a[href],button,summary,[role='button'],[role='menuitem'],input,select,textarea") != null,
        },
      );
      if (shortcut !== null && handler.current(shortcut)) {
        event.preventDefault();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  return {
    cursorId,
    setCursorId,
    selection,
    selectionState: selectionState(selection, rows),
    toggle: (row: InboxRow) => setSelection((selected) => toggledSelection(selected, row)),
    toggleAll: () => setSelection((selected) => toggledAll(selected, rows)),
    clearSelection: () => setSelection(NOTHING),
    resolveSelected,
    isResolving,
    busyIds: actions.busyIds,
    isSheetOpen,
    openSheet: () => setSheetOpen(true),
    closeSheet: () => setSheetOpen(false),
  };
}

export type InboxTriage = ReturnType<typeof useInboxTriage>;
