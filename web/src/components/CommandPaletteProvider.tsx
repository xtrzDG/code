"use client";

/**
 * The command palette's place in the cabinet: Cmd+K (Ctrl+K) opens and
 * closes it from any page of the frame, and `useCommandPalette().open()`
 * opens it from a button (the phone's top bar, the sidebar). The palette
 * lists the pages of the navigation it is given and, inside a business,
 * searches its customers, conversations and bookings. "/" is left alone:
 * it stays the inbox's own search box.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { isPaletteShortcut, type PaletteNavLink } from "@/lib/commandPalette";

import { CommandPalette } from "./CommandPalette";
import type { PaletteSearchScope } from "./CommandPaletteSearch";

interface CommandPaletteContextValue {
  open: () => void;
  isOpen: boolean;
}

const CommandPaletteContext = createContext<CommandPaletteContextValue | null>(null);

/** The palette's opener; null outside the cabinet's frame (no button is shown then). */
export function useCommandPalette(): CommandPaletteContextValue | null {
  return useContext(CommandPaletteContext);
}

export function CommandPaletteProvider({
  links,
  searchScope = null,
  children,
}: {
  links: readonly PaletteNavLink[];
  /** The business whose customers, conversations and bookings it searches; null: pages only. */
  searchScope?: PaletteSearchScope | null;
  children: ReactNode;
}) {
  const [isOpen, setOpen] = useState(false);
  const open = useCallback(() => setOpen(true), []);
  const close = useCallback(() => setOpen(false), []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.isComposing || !isPaletteShortcut(event)) {
        return;
      }
      event.preventDefault();
      setOpen((current) => !current);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const value = useMemo(() => ({ open, isOpen }), [open, isOpen]);

  return (
    <CommandPaletteContext.Provider value={value}>
      {children}
      <CommandPalette open={isOpen} onClose={close} links={links} searchScope={searchScope} />
    </CommandPaletteContext.Provider>
  );
}
