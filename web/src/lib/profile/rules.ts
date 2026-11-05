/**
 * The niche's starter answers in the profile editor: suggestions the owner
 * accepts one by one (or all at once) or edits first. They are never
 * saved by themselves; these helpers only say which suggestions are still
 * new to the owner's own lists.
 */

import type { Schema } from "@/api/types";

/** A rule or question compared the way an owner reads it: case and spaces aside. */
export function sameText(left: string, right: string): boolean {
  return normalized(left) === normalized(right);
}

function normalized(text: string): string {
  return text.trim().replace(/\s+/g, " ").toLocaleLowerCase();
}

/** Suggested rules not on the owner's list yet, in the suggestions' order. */
export function newSuggestions(rules: readonly string[], suggestions: readonly string[]): string[] {
  const known = new Set(rules.map(normalized));
  return suggestions.filter((suggestion) => {
    const key = normalized(suggestion);
    if (key === "" || known.has(key)) {
      return false;
    }
    known.add(key);
    return true;
  });
}

/** The list with `rule` added at the end (once). */
export function withRule(rules: readonly string[], rule: string): string[] {
  return newSuggestions(rules, [rule]).length > 0 ? [...rules, rule.trim()] : [...rules];
}

/** The list with every new suggestion added at the end. */
export function withAllSuggestions(rules: readonly string[], suggestions: readonly string[]): string[] {
  return [...rules, ...newSuggestions(rules, suggestions).map((rule) => rule.trim())];
}

type StarterFaq = Schema<"StarterFaqView">;

/** The niche's frequent questions the business does not answer yet (by the question's words). */
export function newFaqSuggestions(questions: readonly string[], suggestions: readonly StarterFaq[]): StarterFaq[] {
  const known = new Set(questions.map(normalized));
  return suggestions.filter((suggestion) => !known.has(normalized(suggestion.question)));
}

/** Customers' questions the assistant could not answer, not yet among the business's answers. */
export function unansweredQuestions(gaps: readonly Pick<Schema<"ProfileGap">, "kind" | "unanswered_question">[], questions: readonly string[]): string[] {
  const asked = gaps.flatMap((gap) => (gap.kind === "unanswered_question" && gap.unanswered_question ? [gap.unanswered_question] : []));
  return newSuggestions(questions, asked);
}
