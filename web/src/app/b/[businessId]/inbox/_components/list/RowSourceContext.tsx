"use client";

/**
 * Where a conversation's customer came from, as the inbox list knows it,
 * for the open conversation's details (the row no longer shows it on its
 * face). The conversation card itself does not carry it; a conversation
 * opened outside the list's view simply shows no source.
 */

import { createContext, useContext, useMemo, type ReactNode } from "react";

import type { InboxRow } from "../../_lib/inboxModel";

const RowSources = createContext<ReadonlyMap<string, string>>(new Map());

export function RowSourceProvider({ rows, children }: { rows: readonly InboxRow[] | undefined; children: ReactNode }) {
  const sources = useMemo(
    () => new Map((rows ?? []).flatMap((row) => (row.acquisitionSource ? [[row.id, row.acquisitionSource] as const] : []))),
    [rows],
  );
  return <RowSources.Provider value={sources}>{children}</RowSources.Provider>;
}

/** The source code of the conversation (a link's tag, an ad, a number), or null when unknown. */
export function useRowSource(conversationId: string): string | null {
  return useContext(RowSources).get(conversationId) ?? null;
}
