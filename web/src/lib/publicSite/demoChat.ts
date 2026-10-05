/**
 * The landing page's live demo chat, without React: the visitor's
 * conversation key, the starter questions in the visitor's language, the
 * transcript and what a failed send tells the visitor. Every demo turn is
 * a sandbox turn (nothing is booked for real), so the transcript shows
 * what the turn did as a "would" ("A table would be booked").
 */

import type { Schema } from "@/api/types";

export type DemoCard = Schema<"PublicDemoCard">;
export type DemoReply = Schema<"PublicDemoReply">;

/** The longest message the demo takes (the API's PublicDemoMessageText). */
export const DEMO_MESSAGE_MAX_LENGTH = 500;

const SESSION_KEY_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";

/**
 * A fresh conversation key (22 characters of [A-Za-z0-9_-], 132 random
 * bits): one key is one conversation with one demo.
 */
export function newSessionKey(random: (bytes: Uint8Array) => Uint8Array = (bytes) => crypto.getRandomValues(bytes)): string {
  const bytes = random(new Uint8Array(22));
  return Array.from(bytes, (byte) => SESSION_KEY_ALPHABET[byte % 64]).join("");
}

/** Up to three starters in the visitor's language, else in the demo's own language. */
export function startersFor(card: Pick<DemoCard, "starters" | "default_language">, locale: string): string[] {
  const starters = card.starters ?? [];
  const inLocale = starters.filter((starter) => baseLanguage(starter.language) === baseLanguage(locale));
  const chosen = inLocale.length > 0 ? inLocale : starters.filter((starter) => starter.language === card.default_language);
  return chosen.slice(0, 3).map((starter) => starter.text);
}

function baseLanguage(tag: string): string {
  return tag.split(/[-_]/)[0]?.toLowerCase() ?? tag;
}

export type DemoOutcome = "booking" | "request" | "handoff";

export type DemoEntry =
  | { id: number; role: "visitor"; text: string }
  | { id: number; role: "assistant"; text: string; lang: string; outcomes: DemoOutcome[] };

/** What a reply did, in the order the transcript names it. */
export function replyOutcomes(reply: Pick<DemoReply, "is_booking_made" | "is_request_made" | "is_handoff_made">): DemoOutcome[] {
  const outcomes: DemoOutcome[] = [];
  if (reply.is_booking_made) {
    outcomes.push("booking");
  }
  if (reply.is_request_made) {
    outcomes.push("request");
  }
  if (reply.is_handoff_made) {
    outcomes.push("handoff");
  }
  return outcomes;
}

/** A message the visitor may send: trimmed, not empty, within the limit. */
export function cleanDemoMessage(text: string): string | null {
  const trimmed = text.trim();
  return trimmed === "" || trimmed.length > DEMO_MESSAGE_MAX_LENGTH ? null : trimmed;
}

export type DemoFailure = "limit" | "unavailable" | "offline" | "failed";

/** What went wrong with a send, by the API's error code. */
export function demoFailure(code: string | null | undefined): DemoFailure {
  switch (code) {
    case "rate_limited":
      return "limit";
    case "not_found":
      return "unavailable";
    case "network_error":
    case "backend_unavailable":
      return "offline";
    default:
      return "failed";
  }
}

/** Few messages left: the chat says how many (null while there are plenty). */
export function messagesLeftNotice(left: number, threshold = 5): number | null {
  return left <= threshold ? Math.max(0, left) : null;
}
