"use client";

import { useState } from "react";

import type { Schema } from "@/api/types";
import { IconArrowRight, IconRefresh, IconSend, IconSparkles } from "@/components/icons";
import { Button, ButtonLink } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { DEMO_MESSAGE_MAX_LENGTH, messagesLeftNotice, startersFor } from "@/lib/publicSite/demoChat";
import { CREATE_PATH } from "@/lib/navigation";

import { DemoTranscript } from "./DemoTranscript";
import { useDemoChat } from "./useDemoChat";

type DemoCard = Schema<"PublicDemoCard">;

/**
 * The hero's live demo: the visitor picks a kind of business and chats
 * with its demo assistant, which answers like a real one in sandbox
 * (nothing is booked for real). Each demo is its own conversation.
 */
export function DemoChat({ demos, messagesPerHour }: { demos: readonly DemoCard[]; messagesPerHour: number }) {
  const { t } = useI18n();
  const [activeId, setActiveId] = useState(demos[0]?.business_id ?? "");
  const active = demos.find((demo) => demo.business_id === activeId) ?? demos[0];
  if (!active) {
    return null;
  }

  return (
    <section aria-label={t("publicDemo.label")} className="flex w-full flex-col" data-testid="demo-chat">
      {demos.length > 1 ? (
        <div role="group" aria-label={t("publicDemo.pick")} className="flex gap-1.5 overflow-x-auto border-b border-line px-3 py-2.5">
          {demos.map((demo) => (
            <button
              key={demo.business_id}
              type="button"
              aria-pressed={demo.business_id === active.business_id}
              onClick={() => setActiveId(demo.business_id)}
              className={cn(
                "shrink-0 rounded-full border px-3 py-1 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-focus",
                demo.business_id === active.business_id
                  ? "border-accent/40 bg-accent-soft text-accent-ink"
                  : "border-line text-ink-muted hover:bg-surface-muted hover:text-ink",
              )}
            >
              {demo.niche_name}
            </button>
          ))}
        </div>
      ) : null}
      <DemoConversation key={active.business_id} demo={active} messagesPerHour={messagesPerHour} />
    </section>
  );
}

function DemoConversation({ demo, messagesPerHour }: { demo: DemoCard; messagesPerHour: number }) {
  const { t, tp, locale } = useI18n();
  const chat = useDemoChat(demo.business_id, messagesPerHour);
  const [draft, setDraft] = useState("");
  const starters = startersFor(demo, locale, [
    t("publicDemo.genericStarters.hours"),
    t("publicDemo.genericStarters.prices"),
    t("publicDemo.genericStarters.place"),
  ]);
  const left = messagesLeftNotice(chat.messagesLeft);
  const isOut = chat.messagesLeft <= 0 || chat.failure === "limit";

  const submit = (text: string) => {
    void chat.send(text);
    setDraft("");
  };

  return (
    <>
      <div className="flex items-center gap-3 border-b border-line px-4 py-3">
        <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-accent-solid text-on-accent" aria-hidden>
          <IconSparkles className="size-4" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-ink">{demo.business_name}</p>
          <p className="truncate text-xs text-ink-subtle">
            {demo.city ? t("publicDemo.place", { niche: demo.niche_name, city: demo.city }) : demo.niche_name}
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-line px-2 py-0.5 text-xs text-ink-muted">{t("publicDemo.badge")}</span>
        {chat.entries.length > 0 ? (
          <Button variant="ghost" size="sm" onClick={chat.restart} aria-label={t("publicDemo.restart")} title={t("publicDemo.restart")}>
            <IconRefresh className="size-4" aria-hidden />
          </Button>
        ) : null}
      </div>
      <DemoTranscript
        greeting={t("publicDemo.greeting", { business: demo.business_name })}
        entries={chat.entries}
        isSending={chat.isSending}
        failure={chat.failure}
      />
      {chat.entries.length === 0 && starters.length > 0 ? (
        <div className="space-y-1.5 px-4 pb-2">
          <p className="text-xs text-ink-subtle">{t("publicDemo.starters")}</p>
          <div className="flex flex-wrap gap-1.5">
            {starters.map((starter) => (
              <button
                key={starter}
                type="button"
                onClick={() => submit(starter)}
                className="rounded-full border border-line bg-surface px-3 py-1 text-left text-xs text-ink transition-colors hover:bg-surface-muted focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-focus"
              >
                {starter}
              </button>
            ))}
          </div>
        </div>
      ) : null}
      {isOut ? (
        <div className="border-t border-line px-4 py-3">
          <ButtonLink href={CREATE_PATH} size="sm" fullWidth trailingIcon={<IconArrowRight className="size-4" aria-hidden />}>
            {t("publicDemo.cta")}
          </ButtonLink>
        </div>
      ) : (
        <form
          className="flex items-center gap-2 border-t border-line px-3 py-3"
          onSubmit={(event) => {
            event.preventDefault();
            submit(draft);
          }}
        >
          <label className="sr-only" htmlFor={`demo-input-${demo.business_id}`}>
            {t("publicDemo.inputLabel")}
          </label>
          <input
            id={`demo-input-${demo.business_id}`}
            value={draft}
            maxLength={DEMO_MESSAGE_MAX_LENGTH}
            onChange={(event) => setDraft(event.target.value)}
            placeholder={t("publicDemo.placeholder")}
            autoComplete="off"
            className="h-10 min-w-0 flex-1 rounded-xl border border-line-strong bg-canvas px-3 text-sm text-ink placeholder:text-ink-subtle focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-focus"
          />
          <Button type="submit" size="sm" disabled={chat.isSending || draft.trim() === ""} aria-label={t("publicDemo.send")}>
            <IconSend className="size-4" aria-hidden />
          </Button>
        </form>
      )}
      <p className="px-4 pb-3 text-xs text-ink-subtle">
        {t("publicDemo.sandbox")} · {t("publicDemo.privacy")}
        {left !== null && !isOut ? ` · ${tp("publicDemo.messagesLeft", left)}` : null}
      </p>
    </>
  );
}
