"use client";

/**
 * Step 7, "Try your assistant": a live test chat with questions to tap
 * (what customers of this kind of business usually ask, then hours,
 * prices, a booking, a person). Enter in the message box sends; the
 * Continue button goes on. Nothing here reaches real customers.
 */

import { useMemo, useState, type FormEvent } from "react";

import { IconRefresh, IconSend } from "@/components/icons";
import { Button, Input, Spinner } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { stepStates } from "@/lib/tunnel/steps";
import { suggestedQuestions, suggestionKey, type SuggestedQuestion } from "@/lib/tunnel/tryQuestions";

import { StepScreen } from "../StepScreen";
import type { StepContext } from "../flow/stepContext";
import { useTryChat, type TryLine } from "./useTryChat";

function Bubble({ line, onResend }: { line: TryLine; onResend: () => void }) {
  const { t } = useI18n();
  const isYou = line.from === "you";
  return (
    <li className={cn("flex flex-col gap-1", isYou ? "items-end" : "items-start")}>
      <span className="sr-only">{isYou ? t("tunnelLaunch.try.you") : t("tunnelLaunch.try.assistant")}:</span>
      <p
        dir="auto"
        className={cn(
          "max-w-[85%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap shadow-sm",
          isYou ? "rounded-ee-md bg-accent-solid text-on-accent" : "rounded-es-md border border-line bg-surface text-ink",
          line.status === "sending" && "opacity-70",
        )}
      >
        {line.text}
      </p>
      {line.status === "failed" ? (
        <span className="flex items-center gap-2 text-xs text-danger">
          {t("tunnelLaunch.try.failed")}
          <button type="button" className="font-medium underline" onClick={onResend}>
            {t("tunnelLaunch.try.resend")}
          </button>
        </span>
      ) : null}
    </li>
  );
}

export function TryScreen({ ctx }: { ctx: StepContext }) {
  const { t } = useI18n();
  const { scroller, lines, isSending, isHandedOff, hasReply, deliver, restart } = useTryChat(ctx.businessId);
  const [text, setText] = useState("");
  const [asked, setAsked] = useState<ReadonlySet<string>>(() => new Set());
  const faq = ctx.starters.faq;
  const suggestions = useMemo(
    () => suggestedQuestions(faq ?? [], ctx.wizard.niche.takes_bookings, asked),
    [faq, ctx.wizard.niche.takes_bookings, asked],
  );

  const questionText = (question: SuggestedQuestion) =>
    question.kind === "niche" ? question.text : t(`tunnelLaunch.try.questions.${question.key}`);

  const ask = (question: SuggestedQuestion) => {
    setAsked((current) => new Set(current).add(suggestionKey(question)));
    void deliver(questionText(question));
  };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const message = text.trim();
    if (message === "" || isSending) {
      return;
    }
    setText("");
    void deliver(message);
  };

  // Tried before (now or on an earlier visit): on; otherwise "skip for now".
  const hasTried = hasReply || stepStates(ctx.setup).try === "done";
  const goOn = () => {
    ctx.refresh();
    ctx.next();
  };

  return (
    <StepScreen
      step="try"
      title={t("tunnelLaunch.try.title")}
      text={t("tunnelLaunch.try.text")}
      wide
      actions={{ onContinue: goOn, canContinue: hasTried, onBack: ctx.back, onSkip: hasTried ? undefined : () => void ctx.skip("try") }}
    >
      <div className="overflow-hidden rounded-3xl border border-line bg-surface/90 shadow-[0_30px_80px_-50px_var(--accent-solid)] backdrop-blur-md">
        <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-ink">
            <span className="size-2 rounded-full bg-success" aria-hidden />
            {t("tunnelLaunch.try.chatLabel")}
          </h2>
          {lines.length > 0 ? (
            <Button variant="ghost" size="sm" onClick={restart} leadingIcon={<IconRefresh className="size-4" aria-hidden />}>
              {t("tunnelLaunch.try.restart")}
            </Button>
          ) : null}
        </div>

        <div ref={scroller} className="h-[min(22rem,48svh)] overflow-y-auto px-4 py-4 sm:h-[24rem]">
          {lines.length === 0 ? (
            <p className="flex h-full items-center justify-center text-center text-sm text-ink-muted">{t("tunnelLaunch.try.empty")}</p>
          ) : (
            <ol role="log" aria-label={t("tunnelLaunch.try.chatLabel")} aria-live="polite" className="space-y-3">
              {lines.map((line) => (
                <Bubble key={line.key} line={line} onResend={() => void deliver(line.text, line.key)} />
              ))}
            </ol>
          )}
          {isSending ? (
            <p className="mt-3 flex items-center gap-2 text-xs text-ink-muted" role="status">
              <Spinner size="sm" />
              {t("tunnelLaunch.try.typing")}
            </p>
          ) : null}
          {isHandedOff ? <p className="mt-3 rounded-xl bg-info-soft px-3 py-2 text-xs text-info">{t("tunnelLaunch.try.handedOff")}</p> : null}
        </div>

        {suggestions.length > 0 ? (
          <div className="border-t border-line px-4 pt-3">
            <p className="text-xs font-medium text-ink-subtle">{t("tunnelLaunch.try.suggestions")}</p>
            <ul className="mt-2 flex gap-2 overflow-x-auto pb-1 [scrollbar-width:none] sm:flex-wrap sm:overflow-visible">
              {suggestions.map((question) => (
                <li key={suggestionKey(question)} className="shrink-0">
                  <button
                    type="button"
                    disabled={isSending}
                    onClick={() => ask(question)}
                    className="rounded-full border border-accent/40 bg-accent-soft/50 px-3 py-1.5 text-sm text-ink transition-colors hover:bg-accent-soft disabled:opacity-60"
                  >
                    {questionText(question)}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        <form onSubmit={submit} data-enter="own" className="flex items-center gap-2 p-3">
          <Input
            aria-label={t("tunnelLaunch.try.placeholder")}
            placeholder={t("tunnelLaunch.try.placeholder")}
            value={text}
            maxLength={2000}
            dir="auto"
            autoComplete="off"
            onChange={(event) => setText(event.target.value)}
            className="flex-1"
          />
          <Button type="submit" aria-label={t("tunnelLaunch.try.send")} title={t("tunnelLaunch.try.send")} disabled={text.trim() === "" || isSending}>
            <IconSend className="size-4 rtl:-scale-x-100" aria-hidden />
          </Button>
        </form>
      </div>
    </StepScreen>
  );
}
