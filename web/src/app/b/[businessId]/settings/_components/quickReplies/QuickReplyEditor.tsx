"use client";

/**
 * Creating or changing a quick reply: its name in the picker, the
 * shortcut typed after "/", and the text in each language of the
 * business (one is enough). What the API refuses (a shortcut already
 * taken, too many replies) is said in the form.
 */

import { useState, type FormEvent } from "react";

import { describeError } from "@/api/errors";
import { useBusiness } from "@/components/business/BusinessContext";
import { Alert, Button, Field, Input, Sheet } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { QUICK_REPLY_TITLE_MAX_LENGTH, SHORTCUT_MAX_LENGTH, type QuickReplyView } from "@/lib/quickReplies";

import { bodyOf, cleanShortcut, draftErrors, draftOf, editorLanguages, type QuickReplyDraft } from "../../_lib/quickReplies";
import { QUICK_REPLY_REASONS, type useQuickReplies } from "../../_lib/useQuickReplies";
import { VariantField } from "./VariantField";

type QuickRepliesState = ReturnType<typeof useQuickReplies>;

function EditorForm({
  reply,
  state,
  formId,
  onSaved,
}: {
  reply: QuickReplyView | null;
  state: QuickRepliesState;
  formId: string;
  onSaved: () => void;
}) {
  const { t, tp } = useI18n();
  const { business } = useBusiness();
  const languages = editorLanguages(business.languages, business.default_language, reply);
  const [draft, setDraft] = useState<QuickReplyDraft>(() => draftOf(reply, languages));
  const [isSubmitted, setSubmitted] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const errors = draftErrors(draft);
  const shown = isSubmitted ? errors : [];

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitted(true);
    if (errors.length > 0) {
      return;
    }
    setError(null);
    const result = await state.saveReply(bodyOf(draft, languages), reply?.id ?? null);
    if (result.ok) {
      onSaved();
    } else {
      setError(result.error);
    }
  };

  return (
    <form id={formId} onSubmit={(event) => void submit(event)} className="space-y-5" noValidate>
      {error ? (
        <Alert tone="danger">{describeError(error, { t, tp }, undefined, QUICK_REPLY_REASONS).title}</Alert>
      ) : null}
      <Field
        label={t("quickReplies.editor.title")}
        hint={t("quickReplies.editor.titleHint")}
        error={shown.includes("title") ? t("errors.codes.validation_failed") : undefined}
        required
      >
        {(control) => (
          <Input
            {...control}
            value={draft.title}
            maxLength={QUICK_REPLY_TITLE_MAX_LENGTH}
            onChange={(event) => setDraft({ ...draft, title: event.target.value })}
          />
        )}
      </Field>
      <Field
        label={t("quickReplies.editor.shortcut")}
        hint={t("quickReplies.editor.shortcutHint")}
        error={shown.includes("shortcut") ? t("quickReplies.editor.shortcutInvalid") : undefined}
        required
      >
        {(control) => (
          <div className="relative">
            <span aria-hidden className="pointer-events-none absolute start-3 top-1/2 -translate-y-1/2 font-mono text-sm text-ink-subtle">
              /
            </span>
            <Input
              {...control}
              value={draft.shortcut}
              maxLength={SHORTCUT_MAX_LENGTH}
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              className="px-6 font-mono"
              onChange={(event) => setDraft({ ...draft, shortcut: cleanShortcut(event.target.value) })}
            />
          </div>
        )}
      </Field>
      <fieldset className="space-y-3">
        <legend className="mb-1 text-sm font-medium text-ink">{t("quickReplies.editor.texts")}</legend>
        <p className={shown.includes("texts") ? "text-sm text-danger" : "text-sm text-ink-muted"}>
          {shown.includes("texts") ? t("quickReplies.editor.needOneText") : t("quickReplies.editor.textHint")}
        </p>
        {languages.map((language) => (
          <VariantField
            key={language}
            language={language}
            value={draft.texts[language] ?? ""}
            businessName={business.name}
            onChange={(text) => setDraft({ ...draft, texts: { ...draft.texts, [language]: text } })}
          />
        ))}
      </fieldset>
    </form>
  );
}

export function QuickReplyEditor({
  open,
  reply,
  state,
  onClose,
  onSaved,
}: {
  open: boolean;
  /** The reply being changed; null for a new one. */
  reply: QuickReplyView | null;
  state: QuickRepliesState;
  onClose: () => void;
  onSaved: () => void;
}) {
  const { t } = useI18n();
  const formId = "quick-reply-editor";
  return (
    <Sheet
      open={open}
      onClose={onClose}
      title={reply ? t("quickReplies.editor.editTitle") : t("quickReplies.editor.newTitle")}
      description={t("quickReplies.editor.description")}
      className="lg:w-[34rem]"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            {t("quickReplies.editor.cancel")}
          </Button>
          <Button type="submit" form={formId} isLoading={state.isSaving} loadingText={t("quickReplies.editor.saving")}>
            {t("quickReplies.editor.save")}
          </Button>
        </>
      }
    >
      {/* A fresh form for each reply opened (keyed), so a draft never leaks into another. */}
      <EditorForm key={reply?.id ?? "new"} reply={reply} state={state} formId={formId} onSaved={onSaved} />
    </Sheet>
  );
}
