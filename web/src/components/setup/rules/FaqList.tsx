"use client";

/**
 * The ready answers of the Rules screen: a question and its answer per
 * line, each saved by itself; then what customers asked and the assistant
 * could not answer, and the niche's frequent questions, as chips to take.
 * A suggested question with a ready answer is added with it; one without
 * opens its line with the answer to write.
 */

import { useId, useRef } from "react";

import type { Schema } from "@/api/types";
import { IconPlus, IconX } from "@/components/icons";
import { Button, ErrorState, Input, LoadingRegion, SkeletonRows, Textarea } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { newFaqSuggestions, unansweredQuestions } from "@/lib/profile/rules";

import { SaveMark } from "../fields/SaveMark";
import { SuggestionChips } from "./SuggestionChips";
import type { FaqRows } from "./useFaqRows";

type StarterFaq = Schema<"StarterFaqView">;

export function FaqList({ faq, starters, gaps }: { faq: FaqRows; starters: readonly StarterFaq[]; gaps: readonly Schema<"ProfileGap">[] }) {
  const { t } = useI18n();
  const headingId = useId();
  const list = useRef<HTMLOListElement>(null);
  const questions = faq.rows.map((row) => row.question);
  const asked = unansweredQuestions(gaps, questions);
  const offered = newFaqSuggestions(questions, starters);

  /** A new line; the focus goes to its question, or to its answer when the question is given. */
  const open = (question = "", answer = "") => {
    const key = faq.add(question, answer);
    const field = question ? "textarea" : "input";
    requestAnimationFrame(() => list.current?.querySelector<HTMLElement>(`li[data-faq-key="${key}"] ${field}`)?.focus());
  };

  return (
    <section aria-labelledby={headingId} className="space-y-4 rounded-2xl border border-line bg-surface/85 p-5 backdrop-blur-sm sm:p-6">
      <div className="space-y-1">
        <h2 id={headingId} className="text-base font-semibold text-ink">
          {t("profileEdit.rules.faqTitle")}
        </h2>
        <p className="text-sm text-ink-muted">{t("profileEdit.rules.faqHint")}</p>
      </div>
      {faq.error && faq.isLoading ? (
        <ErrorState error={faq.error} onRetry={faq.reload} />
      ) : faq.isLoading ? (
        <LoadingRegion label={t("common.loading")}>
          <SkeletonRows rows={2} />
        </LoadingRegion>
      ) : faq.rows.length === 0 ? (
        <p className="text-sm text-ink-subtle">{t("profileEdit.rules.faqEmpty")}</p>
      ) : (
        <ol ref={list} className="space-y-3">
          {faq.rows.map((row, index) => {
            const name = row.question.trim() || t("profileEdit.rules.removeEmpty");
            return (
              <li key={row.key} data-faq-key={row.key} onBlur={(event) => {
                if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
                  void faq.save(row.key);
                }
              }} className="space-y-2 rounded-xl border border-line bg-surface p-3 sm:p-4">
                <div className="flex items-start gap-2">
                  <Input
                    aria-label={t("profileEdit.rules.questionOf", { number: index + 1 })}
                    placeholder={t("profileEdit.rules.question")}
                    value={row.question}
                    maxLength={300}
                    onChange={(event) => faq.update(row.key, { question: event.target.value })}
                    className="font-medium"
                  />
                  <SaveMark status={faq.status[row.key]} />
                  <Button
                    variant="ghost"
                    size="sm"
                    aria-label={t("profileEdit.rules.removeQuestion", { question: name })}
                    title={t("profileEdit.rules.removeQuestion", { question: name })}
                    onClick={() => void faq.remove(row.key)}
                  >
                    <IconX className="size-4" aria-hidden />
                  </Button>
                </div>
                <Textarea
                  aria-label={t("profileEdit.rules.answerOf", { number: index + 1 })}
                  placeholder={t("profileEdit.rules.answer")}
                  rows={2}
                  value={row.answer}
                  maxLength={8000}
                  onChange={(event) => faq.update(row.key, { answer: event.target.value })}
                />
              </li>
            );
          })}
        </ol>
      )}
      <Button variant="secondary" size="sm" leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={() => open()} disabled={faq.isLoading}>
        {t("profileEdit.rules.addQuestion")}
      </Button>
      {faq.isLoading ? null : (
        <div className="space-y-4">
          <SuggestionChips
            title={t("profileEdit.rules.customersAsked")}
            chips={asked.map((question) => ({ key: question, text: question, label: t("profileEdit.rules.writeAnswer", { question }), onPick: () => open(question) }))}
          />
          <SuggestionChips
            title={t("profileEdit.rules.suggestedQuestions")}
            chips={offered.map((item) => {
              const ready = item.is_ready && item.answer ? item.answer : null;
              return {
                key: item.key,
                text: item.question,
                label: ready ? t("profileEdit.rules.addWithAnswer", { question: item.question }) : t("profileEdit.rules.writeAnswer", { question: item.question }),
                onPick: () => (ready ? faq.add(item.question, ready) : open(item.question)),
              };
            })}
          />
        </div>
      )}
    </section>
  );
}
