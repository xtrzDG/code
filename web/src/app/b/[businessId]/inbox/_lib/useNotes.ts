"use client";

/**
 * The team's internal notes on a conversation: newest first, paged, loaded
 * with the conversation (each read is audited, like the card) and kept
 * fresh by the live stream (`conversation.note`). A new note appears at
 * once; a deleted one goes at once and comes back if the API refuses. The
 * note counts on the inbox rows follow.
 */

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import { queryKeys } from "@/api/queryKeys";
import { useCursorPage } from "@/api/useCursorPage";
import { useMutation } from "@/api/useMutation";
import { useBusiness } from "@/components/business/BusinessContext";

import { rowsWithNoteDelta, type InboxListData } from "./cardUpdates";
import type { ConversationNotePage, ConversationNoteView } from "./types";

export function useNotes(conversationId: string, enabled: boolean) {
  const { business } = useBusiness();
  const key = queryKeys.conversations.notes(business.id, conversationId);
  const notes = useCursorPage<ConversationNoteView, ConversationNotePage>(
    key,
    ({ cursor, limit }) =>
      api.GET("/v1/businesses/{business_id}/conversations/{conversation_id}/notes", {
        params: {
          path: { business_id: business.id, conversation_id: conversationId },
          query: { limit: String(limit), cursor: cursor ?? undefined },
        },
      }),
    { enabled, pageSize: 20 },
  );

  const changeRowCount = (delta: number) =>
    queryCache.update<InboxListData>(queryKeys.conversations.inboxAll(business.id), (data) =>
      rowsWithNoteDelta(data, conversationId, delta),
    );

  const add = useMutation(
    (text: string) =>
      api.POST("/v1/businesses/{business_id}/conversations/{conversation_id}/notes", {
        params: { path: { business_id: business.id, conversation_id: conversationId } },
        body: { text },
      }),
    { stale: [queryKeys.conversations.inboxAll(business.id)] },
  );

  const remove = useMutation(
    (note: ConversationNoteView) =>
      api.DELETE("/v1/businesses/{business_id}/conversations/{conversation_id}/notes/{note_id}", {
        params: { path: { business_id: business.id, conversation_id: conversationId, note_id: note.id } },
      }),
    {
      optimistic: (note) => {
        const undoList = queryCache.update<{ items: ConversationNoteView[] }>(key, (data) => ({
          ...data,
          items: data.items.filter((item) => item.id !== note.id),
        }));
        const undoRows = changeRowCount(-1);
        return () => {
          undoList();
          undoRows();
        };
      },
      stale: [queryKeys.conversations.inboxAll(business.id)],
    },
  );

  const addNote = async (text: string) => {
    const result = await add.run(text.trim());
    if (result.ok) {
      notes.updateItems((items) => [result.data, ...items.filter((item) => item.id !== result.data.id)]);
      changeRowCount(1);
    }
    return result.ok;
  };

  const deleteNote = async (note: ConversationNoteView) => (await remove.run(note)).ok;

  return { notes, addNote, deleteNote, isAdding: add.isPending };
}
