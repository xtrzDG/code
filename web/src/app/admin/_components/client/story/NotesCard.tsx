"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { RequestBody, Schema } from "@/api/types";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { Button, Card, Checkbox, ErrorState, Field, SkeletonRows, Textarea, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { NOTE_MAX, cleanNote, isNoteValid } from "../../../_lib/clientNotes";
import { NoteItem } from "./NoteItem";

type Note = Schema<"ClientNoteView">;

/**
 * The platform team's notes about one client, pinned first then newest:
 * everyone who sees clients reads them; an admin who may write about
 * clients adds, edits, pins and deletes them.
 */
export function NotesCard({ businessId, timeZone, canWrite }: { businessId: string; timeZone: string; canWrite: boolean }) {
  const { t } = useI18n();
  const toast = useToast();
  const key = queryKeys.admin.clientNotes(businessId);
  const notes = useQuery(key, () =>
    api.GET("/v1/admin/clients/{business_id}/notes", { params: { path: { business_id: businessId } } }),
  );
  const [text, setText] = useState("");
  const [isPinned, setPinned] = useState(false);
  const create = useMutation(
    (body: RequestBody<"/v1/admin/clients/{business_id}/notes", "post">) =>
      api.POST("/v1/admin/clients/{business_id}/notes", { params: { path: { business_id: businessId } }, body }),
    { invalidate: [key] },
  );
  const update = useMutation(
    (note: Note, body: RequestBody<"/v1/admin/clients/{business_id}/notes/{note_id}", "patch">) =>
      api.PATCH("/v1/admin/clients/{business_id}/notes/{note_id}", {
        params: { path: { business_id: businessId, note_id: note.id } },
        body,
      }),
    { invalidate: [key] },
  );
  const remove = useMutation(
    (note: Note) =>
      api.DELETE("/v1/admin/clients/{business_id}/notes/{note_id}", {
        params: { path: { business_id: businessId, note_id: note.id } },
      }),
    { invalidate: [key] },
  );

  const onAdd = async () => {
    if (!isNoteValid(text)) {
      return;
    }
    const result = await create.run({ text: cleanNote(text), is_pinned: isPinned });
    if (result.ok) {
      setText("");
      setPinned(false);
      toast.success(t("adminStory.notes.added"));
    }
  };
  const onRemove = async (note: Note) => {
    const result = await remove.run(note);
    if (result.ok) {
      toast.success(t("adminStory.notes.deleted"));
    }
    return result.ok;
  };
  const onChange = async (note: Note, body: RequestBody<"/v1/admin/clients/{business_id}/notes/{note_id}", "patch">) => (await update.run(note, body)).ok;
  const items = notes.data?.items ?? [];

  return (
    <Card title={t("adminStory.notes.title")} description={t("adminStory.notes.description")}>
      {canWrite ? (
        <form
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            void onAdd();
          }}
        >
          <Field
            label={t("adminStory.notes.label")}
            error={text.length > NOTE_MAX ? t("adminStory.notes.tooLong") : undefined}
          >
            {(control) => (
              <Textarea
                {...control}
                value={text}
                rows={3}
                placeholder={t("adminStory.notes.placeholder")}
                onChange={(event) => setText(event.target.value)}
              />
            )}
          </Field>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <Checkbox label={t("adminStory.notes.pinNew")} checked={isPinned} onChange={(event) => setPinned(event.target.checked)} />
            <Button type="submit" size="sm" isLoading={create.isPending} disabled={!isNoteValid(text)}>
              {t("adminStory.notes.add")}
            </Button>
          </div>
        </form>
      ) : (
        <p className="text-sm text-ink-muted">{t("adminStory.notes.readOnly")}</p>
      )}

      <div className="mt-5">
        {notes.error && !notes.data ? (
          <ErrorState error={notes.error} onRetry={notes.reload} />
        ) : !notes.data ? (
          <SkeletonRows rows={2} />
        ) : items.length === 0 ? (
          <p className="text-sm text-ink-muted">{t("adminStory.notes.empty")}</p>
        ) : (
          <ul className="divide-y divide-line border-t border-line">
            {items.map((note) => (
              <NoteItem
                key={note.id}
                note={note}
                timeZone={timeZone}
                canWrite={canWrite}
                isSaving={update.isPending}
                isDeleting={remove.isPending}
                onChange={(body) => onChange(note, body)}
                onRemove={() => onRemove(note)}
              />
            ))}
          </ul>
        )}
      </div>
    </Card>
  );
}
