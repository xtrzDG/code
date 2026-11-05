"use client";

/**
 * The team's internal notes on a conversation, set apart from the
 * conversation with the customer: a warm paper tone, a lock and "only your
 * team sees this". Notes are never sent to the customer or the assistant.
 * The newest are first; the author (or an owner) may delete one.
 */

import { useId, useState } from "react";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { IconTrash } from "@/components/icons";
import { LoadMore } from "@/components/insights/common";
import { formatRelative } from "@/components/insights/dates";
import { Button, ConfirmDialog, ErrorState, LoadingRegion, SkeletonText, Textarea, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { avatarTone } from "../../_lib/team";
import { initialsOf } from "../../_lib/conversationModel";
import type { ConversationNoteView } from "../../_lib/types";
import type { useNotes } from "../../_lib/useNotes";
import { MemberAvatar } from "../MemberAvatar";

const NOTE_MAX_LENGTH = 4000;

function LockGlyph({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" className={className} aria-hidden>
      <rect x="5" y="11" width="14" height="9" rx="2" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" />
    </svg>
  );
}

function NoteItem({ note, onDelete }: { note: ConversationNoteView; onDelete: () => void }) {
  const { t, locale } = useI18n();
  const format = useBusinessFormat();
  const name = note.author_name ?? t("inboxCard.notes.unknownAuthor");
  const when = formatRelative(note.created_at, locale) ?? format.dateTime(note.created_at);
  return (
    <li className="animate-settle rounded-2xl border border-warning/25 bg-warning-soft/60 px-3.5 py-3">
      <div className="flex items-center gap-2">
        <MemberAvatar member={{ initials: initialsOf(note.author_name), tone: avatarTone(note.author_user_id) }} size="xs" />
        <p className="min-w-0 flex-1 truncate text-xs text-ink-muted">
          <span className="font-medium text-ink" data-user-content={note.author_name ? true : undefined}>
            {name}
          </span>
          {" · "}
          <time dateTime={new Date(note.created_at / 1000).toISOString()} title={format.dateTime(note.created_at)}>
            {when}
          </time>
        </p>
        {note.can_delete ? (
          <button
            type="button"
            onClick={onDelete}
            aria-label={t("inboxCard.notes.delete")}
            className="-m-1 flex size-8 shrink-0 cursor-pointer items-center justify-center rounded-md text-ink-subtle hover:bg-danger-soft hover:text-danger"
          >
            <IconTrash className="size-4" aria-hidden />
          </button>
        ) : null}
      </div>
      <p dir="auto" data-user-content className="mt-1.5 text-sm break-words whitespace-pre-wrap text-ink">
        {note.text}
      </p>
    </li>
  );
}

export function NotesPanel({ notes: model }: { notes: ReturnType<typeof useNotes> }) {
  const { t } = useI18n();
  const toast = useToast();
  const id = useId();
  const [text, setText] = useState("");
  const [deleting, setDeleting] = useState<ConversationNoteView | null>(null);
  const { notes } = model;
  const items = notes.items;
  const tooLong = text.length > NOTE_MAX_LENGTH;

  const submit = async (event?: { preventDefault: () => void }) => {
    event?.preventDefault();
    if (!text.trim() || tooLong || model.isAdding) {
      return;
    }
    if (await model.addNote(text)) {
      setText("");
      toast.success(t("inboxCard.notes.added"));
    }
  };

  return (
    <section aria-labelledby={`${id}-title`} className="space-y-4">
      <h3 id={`${id}-title`} className="sr-only">
        {t("inboxCard.notes.title")}
      </h3>
      <form onSubmit={(event) => void submit(event)} className="space-y-2 rounded-2xl border border-dashed border-warning/45 bg-warning-soft/40 p-3">
        <label htmlFor={`${id}-text`} className="flex items-center gap-1.5 text-xs font-semibold text-warning">
          <LockGlyph className="size-3.5" />
          {t("inboxCard.notes.hint")}
        </label>
        <Textarea
          id={`${id}-text`}
          rows={3}
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
              void submit(event);
            }
          }}
          placeholder={t("inboxCard.notes.placeholder")}
          aria-describedby={`${id}-description`}
          aria-invalid={tooLong || undefined}
          className="bg-surface"
        />
        <div className="flex items-center justify-between gap-3">
          <p id={`${id}-description`} className={cn("text-xs", tooLong ? "text-danger" : "text-ink-subtle")}>
            {tooLong
              ? t("inboxCard.notes.length", { count: text.length, max: NOTE_MAX_LENGTH })
              : t("inboxCard.notes.description")}
          </p>
          <Button
            type="submit"
            size="sm"
            disabled={!text.trim() || tooLong}
            isLoading={model.isAdding}
            loadingText={t("inboxCard.notes.adding")}
          >
            {t("inboxCard.notes.add")}
          </Button>
        </div>
      </form>

      {items === undefined ? (
        notes.error ? (
          <ErrorState error={notes.error} onRetry={notes.reload} />
        ) : (
          <LoadingRegion label={t("inboxCard.notes.loading")}>
            <SkeletonText lines={3} />
          </LoadingRegion>
        )
      ) : items.length === 0 ? (
        <p className="px-1 text-sm text-ink-muted">{t("inboxCard.notes.empty")}</p>
      ) : (
        <>
          <ul className="space-y-2.5" aria-label={t("inboxCard.notes.title")}>
            {items.map((note) => (
              <NoteItem key={note.id} note={note} onDelete={() => setDeleting(note)} />
            ))}
          </ul>
          <LoadMore hasMore={notes.hasMore} isLoading={notes.isLoadingMore} error={notes.moreError} onMore={notes.loadMore} />
        </>
      )}

      <ConfirmDialog
        open={deleting !== null}
        title={t("inboxCard.notes.confirmDelete.title")}
        description={t("inboxCard.notes.confirmDelete.description")}
        confirmLabel={t("inboxCard.notes.confirmDelete.confirm")}
        onClose={() => setDeleting(null)}
        onConfirm={async () => {
          const note = deleting;
          setDeleting(null);
          if (note && (await model.deleteNote(note))) {
            toast.success(t("inboxCard.notes.deleted"));
          }
        }}
      />
    </section>
  );
}
