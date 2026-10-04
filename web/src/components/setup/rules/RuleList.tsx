"use client";

/**
 * A list of short rules the assistant follows (when to call a person,
 * what never to promise): each rule a line of its own, added, edited or
 * removed, and the niche's usual rules offered as chips to take. The
 * screen saves the list as it changes.
 */

import { useId, useRef } from "react";

import type { ApiError } from "@/api/errors";
import { IconPlus, IconTrash } from "@/components/icons";
import { Button, Input } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { newSuggestions, withAllSuggestions, withRule } from "@/lib/profile/rules";

import { SaveProblem } from "../edit/SaveProblem";
import { SuggestionChips } from "./SuggestionChips";

const MAX_RULE_LENGTH = 300;
const MAX_RULES = 30;

export function RuleList({
  title,
  hint,
  rules,
  onChange,
  suggestions,
  error,
}: {
  title: string;
  hint: string;
  rules: readonly string[];
  onChange: (rules: string[]) => void;
  /** The niche's usual rules, offered until they are on the list. */
  suggestions: readonly string[];
  error: ApiError | null;
}) {
  const { t } = useI18n();
  const headingId = useId();
  const list = useRef<HTMLUListElement>(null);
  const offered = newSuggestions(rules, suggestions);
  const isFull = rules.length >= MAX_RULES;

  const add = () => {
    onChange([...rules, ""]);
    // The new, empty rule takes the focus once it is drawn.
    requestAnimationFrame(() => list.current?.querySelector<HTMLInputElement>("li:last-child input")?.focus());
  };

  return (
    <section aria-labelledby={headingId} className="space-y-4 rounded-2xl border border-line bg-surface/85 p-5 backdrop-blur-sm sm:p-6">
      <div className="space-y-1">
        <h2 id={headingId} className="text-base font-semibold text-ink">
          {title}
        </h2>
        <p className="text-sm text-ink-muted">{hint}</p>
      </div>
      {rules.length > 0 ? (
        <ul ref={list} className="space-y-2">
          {rules.map((rule, index) => {
            const name = rule.trim() || t("profileEdit.rules.rule", { number: index + 1 });
            return (
              <li key={index} className="flex items-center gap-2">
                <Input
                  aria-label={`${title}: ${t("profileEdit.rules.rule", { number: index + 1 })}`}
                  value={rule}
                  maxLength={MAX_RULE_LENGTH}
                  placeholder={t("profileEdit.rules.rulePlaceholder")}
                  onChange={(event) => onChange(rules.map((item, position) => (position === index ? event.target.value : item)))}
                />
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label={t("profileEdit.rules.removeRule", { rule: name })}
                  title={t("profileEdit.rules.removeRule", { rule: name })}
                  onClick={() => onChange(rules.filter((_, position) => position !== index))}
                >
                  <IconTrash className="size-4" aria-hidden />
                </Button>
              </li>
            );
          })}
        </ul>
      ) : null}
      <SaveProblem error={error} />
      <Button variant="secondary" size="sm" leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={add} disabled={isFull}>
        {t("profileEdit.rules.addRule")}
      </Button>
      {isFull ? null : (
        <SuggestionChips
          title={t("profileEdit.rules.suggested")}
          chips={offered.map((rule) => ({
            key: rule,
            text: rule,
            label: t("profileEdit.rules.addSuggestion", { rule }),
            onPick: () => onChange(withRule(rules, rule)),
          }))}
          action={
            offered.length > 1 ? (
              <Button variant="ghost" size="sm" onClick={() => onChange(withAllSuggestions(rules, offered).slice(0, MAX_RULES))}>
                {t("profileEdit.rules.addAll")}
              </Button>
            ) : undefined
          }
        />
      )}
    </section>
  );
}
