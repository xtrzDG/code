"use client";

/**
 * Settings → Quick replies (owners): the replies the team sends often,
 * each in the languages of the business. In a conversation staff type "/"
 * to insert one, with the customer's name and booking filled in.
 */

import { useState } from "react";

import { IconChat, IconPencil, IconPlus, IconTrash } from "@/components/icons";
import { Button, Card, ConfirmDialog, EmptyState, ErrorState, LoadingRegion, PageHeader, SkeletonCard, useToast } from "@/components/ui";
import { AnimatedPresenceList } from "@/components/motion";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";
import type { QuickReplyView } from "@/lib/quickReplies";

import { useQuickReplies } from "../_lib/useQuickReplies";
import { QuickReplyEditor } from "./quickReplies/QuickReplyEditor";

function QuickReplyCard({ reply, onEdit, onDelete }: { reply: QuickReplyView; onEdit: () => void; onDelete: () => void }) {
  const { t, locale } = useI18n();
  const first = reply.variants[0];
  return (
    <article className="flex h-full flex-col gap-3 rounded-2xl border border-line bg-surface p-4 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <p className="font-mono text-xs text-accent-ink" dir="auto">
            /{reply.shortcut}
          </p>
          <h3 className="mt-0.5 truncate text-base font-semibold text-ink" dir="auto">
            {reply.title}
          </h3>
        </div>
        <div className="flex shrink-0 gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={onEdit}
            aria-label={t("quickReplies.editLabel", { title: reply.title })}
            leadingIcon={<IconPencil className="size-4" aria-hidden />}
          >
            <span className="sr-only sm:not-sr-only">{t("quickReplies.edit")}</span>
          </Button>
          <Button
            variant="danger-ghost"
            size="sm"
            onClick={onDelete}
            aria-label={t("quickReplies.deleteLabel", { title: reply.title })}
            leadingIcon={<IconTrash className="size-4" aria-hidden />}
          >
            <span className="sr-only">{t("quickReplies.delete")}</span>
          </Button>
        </div>
      </div>
      {first ? (
        <p dir="auto" lang={first.language} className="line-clamp-3 text-sm whitespace-pre-wrap text-ink-muted">
          {first.text}
        </p>
      ) : null}
      <dl className="mt-auto flex flex-wrap gap-x-4 gap-y-1.5 border-t border-line pt-3 text-xs">
        <div className="flex flex-wrap items-center gap-1.5">
          <dt className="text-ink-subtle">{t("quickReplies.languages")}:</dt>
          {reply.variants.map((variant) => (
            <dd key={variant.language} className="rounded-full bg-surface-muted px-2 py-0.5 text-ink-muted">
              {languageName(variant.language, locale)}
            </dd>
          ))}
        </div>
        {(reply.variables ?? []).length > 0 ? (
          <div className="flex flex-wrap items-center gap-1.5">
            <dt className="text-ink-subtle">{t("quickReplies.variablesUsed")}:</dt>
            {(reply.variables ?? []).map((variable) => (
              <dd key={variable} className="rounded-full bg-accent-soft px-2 py-0.5 text-accent-ink">
                {t(`quickReplies.variables.${variable}`)}
              </dd>
            ))}
          </div>
        ) : null}
      </dl>
    </article>
  );
}

export function QuickRepliesTab() {
  const { t } = useI18n();
  const toast = useToast();
  const state = useQuickReplies();
  const [editing, setEditing] = useState<{ reply: QuickReplyView | null } | null>(null);
  const [deleting, setDeleting] = useState<QuickReplyView | null>(null);
  const replies = state.list.data?.items;

  const addButton = (
    <Button leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={() => setEditing({ reply: null })}>
      {t("quickReplies.add")}
    </Button>
  );

  return (
    <>
      <PageHeader
        title={t("navigation.pages.settingsQuickReplies")}
        description={t("quickReplies.description")}
        actions={replies && replies.length > 0 ? addButton : undefined}
      />
      {replies === undefined ? (
        state.list.error ? (
          <ErrorState error={state.list.error} onRetry={state.list.reload} className="py-6" />
        ) : (
          <LoadingRegion label={t("quickReplies.loading")} className="grid gap-4 md:grid-cols-2">
            <SkeletonCard lines={3} />
            <SkeletonCard lines={3} />
          </LoadingRegion>
        )
      ) : replies.length === 0 ? (
        <Card>
          <EmptyState
            icon={<IconChat className="size-6" />}
            title={t("quickReplies.emptyTitle")}
            description={t("quickReplies.emptyDescription")}
            action={addButton}
          />
        </Card>
      ) : (
        <AnimatedPresenceList
          items={replies}
          getKey={(reply) => reply.id}
          className="grid gap-4 md:grid-cols-2"
          renderItem={(reply) => (
            <QuickReplyCard reply={reply} onEdit={() => setEditing({ reply })} onDelete={() => setDeleting(reply)} />
          )}
        />
      )}

      <QuickReplyEditor
        open={editing !== null}
        reply={editing?.reply ?? null}
        state={state}
        onClose={() => setEditing(null)}
        onSaved={() => {
          setEditing(null);
          toast.success(t("quickReplies.saved"));
        }}
      />
      <ConfirmDialog
        open={deleting !== null}
        title={t("quickReplies.confirmDelete.title")}
        description={t("quickReplies.confirmDelete.description", { title: deleting?.title ?? "" })}
        confirmLabel={t("quickReplies.confirmDelete.confirm")}
        onClose={() => setDeleting(null)}
        onConfirm={async () => {
          const reply = deleting;
          setDeleting(null);
          if (reply && (await state.deleteReply(reply)).ok) {
            toast.success(t("quickReplies.deleted"));
          }
        }}
      />
    </>
  );
}
