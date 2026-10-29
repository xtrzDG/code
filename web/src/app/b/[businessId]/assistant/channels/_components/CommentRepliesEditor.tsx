"use client";

import { useId, useState, type FormEvent, type KeyboardEvent } from "react";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useBusiness } from "@/components/business/BusinessContext";
import { Switch } from "@/components/content/Switch";
import { IconX } from "@/components/icons";
import { Alert, Button, Field, Input, Textarea, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

import { upsertChannel, type ChannelView } from "../_lib/channels";
import {
  addKeyword,
  buildCommentRepliesBody,
  commentRepliesForm,
  isSavedReplies,
  MAX_REPLY_LENGTH,
  type CommentRepliesBody,
  type CommentRepliesForm,
  type CommentRepliesProblem,
  type KeywordProblem,
} from "../_lib/commentReplies";

const PROBLEMS: Record<CommentRepliesProblem | KeywordProblem, MessageKey> = {
  keywordsMissing: "metaConnect.commentReplies.errors.keywordsMissing",
  replyMissing: "metaConnect.commentReplies.errors.replyMissing",
  keyword: "metaConnect.commentReplies.errors.keyword",
  tooMany: "metaConnect.commentReplies.errors.tooMany",
};

/**
 * On the Instagram card: comment-to-DM. When a comment under a post names
 * one of the keywords, the assistant sends its author one message in
 * Direct. Owners turn it on and edit the keywords and the message; staff
 * see whether it is on. Until the release that answers comments, the card
 * says so and keeps the settings.
 */
export function CommentRepliesEditor({ channel, canManage }: { channel: ChannelView; canManage: boolean }) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const id = useId();
  const saved = channel.comment_replies;
  const [form, setForm] = useState<CommentRepliesForm>(() => commentRepliesForm(saved ?? { is_on: false, is_available: false }));
  const [typed, setTyped] = useState("");
  const [keywordProblem, setKeywordProblem] = useState<KeywordProblem | CommentRepliesProblem | null>(null);
  const [replyProblem, setReplyProblem] = useState<CommentRepliesProblem | null>(null);
  const save = useMutation((body: CommentRepliesBody) =>
    api.PUT("/v1/businesses/{business_id}/channels/instagram/comment-replies", {
      params: { path: { business_id: business.id } },
      body,
    }),
  );
  if (!saved) {
    return null;
  }
  const isDirty = !isSavedReplies(form, saved);

  const add = () => {
    const result = addKeyword(form.keywords, typed);
    setKeywordProblem(result.problem);
    if (result.problem === null) {
      setForm((current) => ({ ...current, keywords: result.keywords }));
      setTyped("");
    }
  };
  const onKeywordKey = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      event.preventDefault();
      add();
    }
  };
  const remove = (word: string) => setForm((current) => ({ ...current, keywords: current.keywords.filter((kept) => kept !== word) }));

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const built = buildCommentRepliesBody(form);
    if (!built.ok) {
      setKeywordProblem(built.problems.includes("keywordsMissing") ? "keywordsMissing" : null);
      setReplyProblem(built.problems.includes("replyMissing") ? "replyMissing" : null);
      return;
    }
    const result = await save.run(built.body);
    if (result.ok) {
      queryCache.update<ChannelView[]>(queryKeys.channels.list(business.id), (list) => upsertChannel(list, result.data));
      toast.success(t("metaConnect.commentReplies.savedToast"));
    }
  };

  const summary = saved.is_on
    ? t("metaConnect.commentReplies.summaryOn", { keywords: (saved.keywords ?? []).join(", ") })
    : t("metaConnect.commentReplies.summaryOff");

  return (
    <section aria-labelledby={`${id}-title`} className="mt-4 space-y-3 border-t border-line pt-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h4 id={`${id}-title`} className="text-sm font-semibold text-ink">
            {t("metaConnect.commentReplies.title")}
          </h4>
          <p className="mt-1 text-sm break-words text-ink-muted" dir="auto">
            {summary}
          </p>
        </div>
        {canManage ? (
          <Switch
            checked={form.isOn}
            onChange={(isOn) => setForm((current) => ({ ...current, isOn }))}
            label={t("metaConnect.commentReplies.toggle")}
            describedBy={`${id}-description`}
          />
        ) : null}
      </div>
      <p id={`${id}-description`} className="text-sm text-ink-muted">
        {t("metaConnect.commentReplies.description")}
      </p>
      {!saved.is_available ? <Alert tone="info">{t("metaConnect.commentReplies.unavailable")}</Alert> : null}

      {canManage && (form.isOn || isDirty) ? (
        <form noValidate onSubmit={(event) => void submit(event)} className="space-y-3">
          <Field
            label={t("metaConnect.commentReplies.keywords")}
            hint={t("metaConnect.commentReplies.keywordsHint")}
            error={keywordProblem ? t(PROBLEMS[keywordProblem]) : undefined}
          >
            {(control) => (
              <div className="flex gap-2">
                <Input
                  {...control}
                  value={typed}
                  maxLength={60}
                  placeholder={t("metaConnect.commentReplies.keywordInput")}
                  onChange={(event) => {
                    setTyped(event.target.value);
                    setKeywordProblem(null);
                  }}
                  onKeyDown={onKeywordKey}
                />
                <Button type="button" variant="secondary" onClick={add} disabled={typed.trim() === ""}>
                  {t("metaConnect.commentReplies.addKeyword")}
                </Button>
              </div>
            )}
          </Field>
          {form.keywords.length > 0 ? (
            <ul className="flex flex-wrap gap-2" aria-label={t("metaConnect.commentReplies.keywords")}>
              {form.keywords.map((word) => (
                <li key={word} className="inline-flex max-w-full items-center gap-1 rounded-full bg-accent-soft py-1 ps-3 pe-1 text-sm text-ink">
                  <span className="truncate" dir="auto">
                    {word}
                  </span>
                  <button
                    type="button"
                    onClick={() => remove(word)}
                    aria-label={t("metaConnect.commentReplies.removeKeyword", { keyword: word })}
                    className="rounded-full p-1 text-ink-muted hover:bg-surface hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-focus"
                  >
                    <IconX aria-hidden className="size-3.5" />
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
          <Field
            label={t("metaConnect.commentReplies.replyText")}
            hint={t("metaConnect.commentReplies.replyHint")}
            error={replyProblem ? t(PROBLEMS[replyProblem]) : undefined}
          >
            {(control) => (
              <Textarea
                {...control}
                rows={3}
                maxLength={MAX_REPLY_LENGTH}
                value={form.replyText}
                onChange={(event) => {
                  const replyText = event.target.value;
                  setForm((current) => ({ ...current, replyText }));
                  setReplyProblem(null);
                }}
              />
            )}
          </Field>
          <Button type="submit" size="sm" variant="secondary" isLoading={save.isPending} loadingText={t("metaConnect.commentReplies.saving")} disabled={!isDirty}>
            {t("metaConnect.commentReplies.save")}
          </Button>
        </form>
      ) : null}
    </section>
  );
}
