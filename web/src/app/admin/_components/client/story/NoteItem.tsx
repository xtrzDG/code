"use client";

import { useState } from "react";

import type { RequestBody, Schema } from "@/api/types";
import { Badge, Button, ConfirmDialog, Field, Textarea, UserContent, UserSentence } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { cleanNote, isNoteEdited, isNoteValid, NOTE_MAX } from "../../../_lib/clientNotes";
import { useClientFormat } from "../../../_lib/useClientFormat";

type Note = Schema<"ClientNoteView">;

/** One note: its words, who wrote it and when; pin, edit and delete for an admin who may write. */
export function NoteItem({
  note,
  timeZone,
  canWrite,
  isSaving,
  isDeleting,
  onChange,
  onRemove,
}: {
  note: Note;
  timeZone: string;
  canWrite: boolean;
  isSaving: boolean;
  isDeleting: boolean;
  onChange: (body: RequestBody<"/v1/admin/clients/{business_id}/notes/{note_id}", "patch">) => Promise<boolean>;
  onRemove: () => Promise<boolean>;
}) {
  const { t } = useI18n();
  const { dateTime } = useClientFormat(timeZone);
  const [draft, setDraft] = useState<string | null>(null);
  const [isConfirming, setConfirming] = useState(false);

  const save = async () => {
    if (draft !== null && isNoteValid(draft) && (await onChange({ text: cleanNote(draft) }))) {
      setDraft(null);
    }
  };
  const remove = async () => {
    if (await onRemove()) {
      setConfirming(false);
    }
  };

  return (
    <li className="py-3">
      {draft === null ? (
        <p dir="auto" className="text-sm break-words whitespace-pre-wrap text-ink">
          {note.is_pinned ? (
            <Badge tone="accent" className="me-2 align-middle">
              {t("adminStory.notes.pinned")}
            </Badge>
          ) : null}
          <UserContent>{note.text}</UserContent>
        </p>
      ) : (
        <Field label={t("adminStory.notes.edit")} error={draft.length > NOTE_MAX ? t("adminStory.notes.tooLong") : undefined}>
          {(control) => <Textarea {...control} value={draft} rows={3} onChange={(event) => setDraft(event.target.value)} />}
        </Field>
      )}
      <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-ink-subtle">
          <span dir="auto">
            {/* The author's name is user content; "Unknown" is ours. */}
            {note.author_name ? (
              <UserSentence text={t("adminStory.notes.byline", { date: dateTime(note.created_at) })} values={{ name: note.author_name }} />
            ) : (
              t("adminStory.notes.byline", { name: t("adminStory.notes.unknownAuthor"), date: dateTime(note.created_at) })
            )}
          </span>
          {isNoteEdited(note) ? <span> · {t("adminStory.notes.edited", { date: dateTime(note.updated_at) })}</span> : null}
        </p>
        {canWrite ? (
          <div className="flex flex-wrap gap-1">
            {draft === null ? (
              <>
                <Button size="sm" variant="ghost" disabled={isSaving} onClick={() => void onChange({ is_pinned: !note.is_pinned })}>
                  {t(note.is_pinned ? "adminStory.notes.unpin" : "adminStory.notes.pin")}
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setDraft(note.text)}>
                  {t("adminStory.notes.edit")}
                </Button>
                <Button size="sm" variant="danger-ghost" onClick={() => setConfirming(true)}>
                  {t("adminStory.notes.delete")}
                </Button>
              </>
            ) : (
              <>
                <Button size="sm" variant="ghost" onClick={() => setDraft(null)}>
                  {t("adminStory.notes.cancel")}
                </Button>
                <Button size="sm" isLoading={isSaving} disabled={!isNoteValid(draft)} onClick={() => void save()}>
                  {t("adminStory.notes.save")}
                </Button>
              </>
            )}
          </div>
        ) : null}
      </div>
      <ConfirmDialog
        open={isConfirming}
        onClose={() => setConfirming(false)}
        onConfirm={remove}
        isPending={isDeleting}
        title={t("adminStory.notes.deleteTitle")}
        description={t("adminStory.notes.deleteDescription")}
        confirmLabel={t("adminStory.notes.delete")}
      />
    </li>
  );
}
