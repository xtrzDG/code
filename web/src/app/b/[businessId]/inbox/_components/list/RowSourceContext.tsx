"use client";

/**
 * What the inbox list knows about its rows, for the open conversation:
 *
 * - where the customer came from (the row no longer shows it on its face),
 *   for the conversation's details; the card itself does not carry it;
 * - who the customer is (name, number), so a conversation on its way shows
 *   its header at once and the row's customer can morph into it
 *   (ConversationHeaderPreview).
 *
 * A conversation opened outside the list's view simply has neither.
 */

import { createContext, useContext, useMemo, type ReactNode } from "react";

import type { InboxRow } from "../../_lib/inboxModel";

/** The customer of a row, as its header shows them before the card arrives. */
export type RowPreview = Pick<InboxRow, "id" | "contactName" | "contactPhone">;

interface RowFacts {
  sources: ReadonlyMap<string, string>;
  previews: ReadonlyMap<string, RowPreview>;
}

const RowFactsContext = createContext<RowFacts>({ sources: new Map(), previews: new Map() });

export function RowSourceProvider({ rows, children }: { rows: readonly InboxRow[] | undefined; children: ReactNode }) {
  const facts = useMemo(
    () => ({
      sources: new Map((rows ?? []).flatMap((row) => (row.acquisitionSource ? [[row.id, row.acquisitionSource] as const] : []))),
      previews: new Map(
        (rows ?? []).map((row) => [row.id, { id: row.id, contactName: row.contactName, contactPhone: row.contactPhone }] as const),
      ),
    }),
    [rows],
  );
  return <RowFactsContext.Provider value={facts}>{children}</RowFactsContext.Provider>;
}

/** The source code of the conversation (a link's tag, an ad, a number), or null when unknown. */
export function useRowSource(conversationId: string): string | null {
  return useContext(RowFactsContext).sources.get(conversationId) ?? null;
}

/** The customer of a conversation the list shows, or null. */
export function useRowPreview(conversationId: string | null): RowPreview | null {
  const previews = useContext(RowFactsContext).previews;
  return conversationId === null ? null : (previews.get(conversationId) ?? null);
}
