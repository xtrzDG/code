/**
 * Questions offered as one-tap chips in "Try it": what customers of this
 * niche usually ask (the starter frequent questions) and the questions
 * every business gets (hours, prices, a booking where the niche books),
 * without repeats, at most MAX_SUGGESTIONS.
 */

import type { Schema } from "@/api/types";

export const MAX_SUGGESTIONS = 4;

/** A general question, written in the dictionary (tunnelLaunch.try.questions.*). */
export type GeneralQuestion = "hours" | "price" | "booking" | "person";

export type SuggestedQuestion = { kind: "niche"; text: string } | { kind: "general"; key: GeneralQuestion };

/** The general questions for a niche: a booking only where it takes bookings. */
export function generalQuestions(takesBookings: boolean): GeneralQuestion[] {
  return takesBookings ? ["booking", "hours", "price", "person"] : ["hours", "price", "person"];
}

/** Two niche questions first (they show the assistant knows the trade), then general ones. */
export function suggestedQuestions(
  faq: readonly Schema<"StarterFaqView">[],
  takesBookings: boolean,
  asked: ReadonlySet<string> = new Set(),
): SuggestedQuestion[] {
  const niche: SuggestedQuestion[] = faq
    .map((entry) => entry.question.trim())
    .filter((text) => text !== "" && !asked.has(text))
    .slice(0, 2)
    .map((text) => ({ kind: "niche", text }));
  const general: SuggestedQuestion[] = generalQuestions(takesBookings)
    .filter((key) => !asked.has(key))
    .map((key) => ({ kind: "general", key }));
  return [...niche, ...general].slice(0, MAX_SUGGESTIONS);
}

/** A key for a suggestion, so an asked one is not offered again. */
export function suggestionKey(question: SuggestedQuestion): string {
  return question.kind === "niche" ? question.text : question.key;
}

/** A fresh test-chat session key (the API keeps parallel test chats apart by it). */
export function newTrySessionKey(random: () => number = Math.random): string {
  const letters = "abcdefghijklmnopqrstuvwxyz0123456789";
  let key = "tunnel";
  for (let index = 0; index < 16; index += 1) {
    key += letters[Math.floor(random() * letters.length)] ?? "a";
  }
  return key;
}
