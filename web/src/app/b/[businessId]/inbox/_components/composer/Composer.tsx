"use client";

/**
 * The reply box at the foot of a conversation: on phones it stays at the
 * bottom of the screen (sticky, above the home indicator) with the quick
 * actions over it, so a person can reply, call, book or resolve without
 * scrolling. Typing "/" opens the quick replies; what they could not fill
 * in is asked for before sending. Ctrl+Enter (⌘+Enter) sends.
 */

import { useId, useLayoutEffect, useRef, type FormEvent, type KeyboardEvent, type ReactNode } from "react";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { IconSend } from "@/components/icons";
import type { ConversationSummaryView, MessageView, StaffReplyView } from "@/components/insights/types";
import { Button, Textarea } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { placeholdersIn } from "@/lib/quickReplies";

import { isWindowClosingSoon, templateLanguageName } from "../../_lib/conversationModel";
import type { FilledQuickReplyView } from "../../_lib/types";
import { useQuickReplyPicker } from "../../_lib/useQuickReplyPicker";
import { useStaffReply } from "../../_lib/useStaffReply";
import { PlaceholderFill } from "./PlaceholderFill";
import { QuickReplyPicker } from "./QuickReplyPicker";
import { ReplyNotice } from "./ReplyNotice";

/** The reply box grows up to about six lines, then scrolls. */
const MAX_TEXT_HEIGHT_PX = 160;

export function Composer({
  conversation,
  reply,
  draft,
  onDraft,
  onSent,
  onRefused,
  actions,
  nowMs,
}: {
  conversation: ConversationSummaryView;
  reply: StaffReplyView | null;
  draft: string;
  onDraft: (text: string) => void;
  onSent: (message: MessageView) => void;
  onRefused: () => void;
  /** The quick actions (Resolve, Call, Book) above the text. */
  actions: ReactNode;
  /** When the card was opened (for "the window closes soon"). */
  nowMs: number;
}) {
  return (
    <div className="sticky bottom-0 z-10 -mx-4 -mb-6 border-t border-line bg-canvas/90 px-4 pt-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] backdrop-blur-xl sm:-mx-6 sm:px-6 lg:static lg:mx-0 lg:mb-0 lg:rounded-b-2xl lg:border lg:border-t-0 lg:bg-surface lg:px-4 lg:pb-3 lg:backdrop-blur-none">
      {actions}
      {reply ? (
        <ReplyForm
          conversation={conversation}
          reply={reply}
          draft={draft}
          onDraft={onDraft}
          onSent={onSent}
          onRefused={onRefused}
          nowMs={nowMs}
        />
      ) : null}
    </div>
  );
}

function ReplyForm({
  conversation,
  reply,
  draft,
  onDraft,
  onSent,
  onRefused,
  nowMs,
}: {
  conversation: ConversationSummaryView;
  reply: StaffReplyView;
  draft: string;
  onDraft: (text: string) => void;
  onSent: (message: MessageView) => void;
  onRefused: () => void;
  nowMs: number;
}) {
  const { t, locale } = useI18n();
  const format = useBusinessFormat();
  const id = useId();
  const textRef = useRef<HTMLTextAreaElement>(null);
  const staffReply = useStaffReply({ conversation, reply, onSent, onRefused });
  const picker = useQuickReplyPicker(conversation.id, draft);
  const placeholders = placeholdersIn(draft);
  const { template, channel } = staffReply;

  // The box grows with the text up to a few lines (every browser; field-sizing is not everywhere yet).
  useLayoutEffect(() => {
    const element = textRef.current;
    if (element) {
      element.style.height = "auto";
      element.style.height = `${Math.min(element.scrollHeight, MAX_TEXT_HEIGHT_PX)}px`;
    }
  }, [draft]);

  const changeDraft = (text: string) => {
    onDraft(text);
    picker.onDraft(text);
  };

  const pick = (chosen: FilledQuickReplyView) => {
    changeDraft(chosen.text);
    picker.close();
    textRef.current?.focus();
  };

  const submit = async (event?: FormEvent) => {
    event?.preventDefault();
    if (await staffReply.submit(draft)) {
      changeDraft("");
    }
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (picker.isOpen && picker.matches.length > 0) {
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        picker.move(event.key === "ArrowDown" ? 1 : -1);
        return;
      }
      if ((event.key === "Enter" || event.key === "Tab") && picker.active) {
        event.preventDefault();
        pick(picker.active);
        return;
      }
    }
    if (picker.isOpen && event.key === "Escape") {
      event.preventDefault();
      picker.close();
      return;
    }
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      void submit();
    }
  };

  const notice = <ReplyNotice conversation={conversation} reply={reply} staffReply={staffReply} />;
  if (!staffReply.canWrite) {
    return notice;
  }

  const length = staffReply.lengthOf(draft);
  const tooLong = staffReply.isTooLong(draft);
  const listId = `${id}-replies`;
  const closesSoon = isWindowClosingSoon(reply.window_closes_at, nowMs);

  return (
    <div className="relative">
      {notice}
      <PlaceholderFill draft={draft} placeholders={placeholders} onDraft={changeDraft} />
      <QuickReplyPicker listId={listId} picker={picker} onPick={pick} />
      <form onSubmit={(event) => void submit(event)} className="flex items-end gap-2">
        <button
          type="button"
          onClick={() => (picker.isOpen ? picker.close() : picker.open())}
          aria-label={t("inboxCard.quickReplies.open")}
          aria-expanded={picker.isOpen}
          title={t("inboxCard.quickReplies.hint")}
          className={cn(
            "flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-full border border-line font-mono text-lg text-ink-muted transition-colors hover:bg-surface-muted hover:text-ink",
            picker.isOpen && "border-accent/40 bg-accent-soft text-accent-ink",
          )}
        >
          /
        </button>
        <label htmlFor={`${id}-text`} className="sr-only">
          {t("conversations.reply.label")}
        </label>
        <Textarea
          ref={textRef}
          id={`${id}-text`}
          rows={1}
          value={draft}
          onChange={(event) => changeDraft(event.target.value)}
          onKeyDown={onKeyDown}
          placeholder={t("inboxCard.composer.placeholder")}
          aria-describedby={`${id}-hint`}
          aria-invalid={tooLong || undefined}
          aria-autocomplete="list"
          aria-controls={picker.isOpen ? listId : undefined}
          aria-activedescendant={picker.isOpen && picker.active ? `${listId}-${picker.active.id}` : undefined}
          disabled={staffReply.isSending}
          className="max-h-40 min-h-11 resize-none overflow-y-auto rounded-3xl py-2.5 text-[0.9375rem] leading-6"
        />
        <Button
          type="submit"
          aria-label={template ? t("conversations.reply.template.send") : t("inboxCard.composer.sendLabel")}
          className="size-11 shrink-0 rounded-full px-0"
          disabled={!staffReply.isSendable(draft)}
          isLoading={staffReply.isSending}
        >
          {staffReply.isSending ? null : <IconSend className="size-5 rtl:-scale-x-100" aria-hidden />}
        </Button>
      </form>
      <div id={`${id}-hint`} className="mt-1.5 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5 px-1 text-xs text-ink-subtle">
        <p className={cn("min-w-0", closesSoon && !template && "font-medium text-warning")}>
          {template
            ? t("conversations.reply.template.hint", {
                name: template.name,
                language: templateLanguageName(template.language_code, locale),
              })
            : reply.is_available && reply.window_closes_at
              ? t("conversations.reply.windowOpenUntil", { channel, date: format.dateTime(reply.window_closes_at) })
              : reply.delivery === "stored_for_widget"
                ? t("conversations.reply.widgetHint")
                : t("conversations.reply.channelHint", { channel })}
        </p>
        {draft ? (
          <p className={cn("tabular-nums", tooLong && "text-danger")}>
            {t("conversations.reply.length", { count: length, max: staffReply.maxLength })}
          </p>
        ) : (
          // The "/" button says it on phones, where every line counts.
          <p className="hidden sm:block">{t("inboxCard.quickReplies.hint")}</p>
        )}
      </div>
    </div>
  );
}
