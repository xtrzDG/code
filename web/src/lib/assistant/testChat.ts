/** Pure helpers of the Assistant section's test chat: sessions kept in the browser and messages. */

import type { Schema } from "@/api/types";

import { CHAT_TARGETS, type ChatTarget } from "./chatTargets";

export type MessageView = Schema<"MessageView">;

const SESSION_SUFFIX_BYTES = 10;

/** Cryptographically strong random bytes from the browser (or Node in tests). */
function secureRandomBytes(length: number): Uint8Array {
  return globalThis.crypto.getRandomValues(new Uint8Array(length));
}

/**
 * A test chat session key the API accepts: ^[A-Za-z0-9][A-Za-z0-9_-]*$, at
 * most 64. The suffix comes from crypto.getRandomValues, so keys cannot be
 * guessed from the time.
 */
export function newSessionKey(
  now: number = Date.now(),
  randomBytes: (length: number) => Uint8Array = secureRandomBytes,
): string {
  const suffix = Array.from(randomBytes(SESSION_SUFFIX_BYTES), (byte) => (byte % 36).toString(36)).join("");
  return `web-${now.toString(36)}-${suffix}`;
}

const SESSION_KEY = /^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/;

export function isSessionKey(value: unknown): value is string {
  return typeof value === "string" && SESSION_KEY.test(value);
}

/** Tool call input or result as readable JSON; text that is not JSON stays as it is. */
export function prettyJson(text: string): string {
  try {
    return JSON.stringify(JSON.parse(text), null, 2);
  } catch {
    return text;
  }
}

/**
 * The test chat remembered in the browser tab, so a reload keeps the
 * conversation: who it talks to and the version that answers it (set by
 * the first answer when the API picked it).
 */
export interface StoredTestChat {
  sessionKey: string;
  versionId: string | null;
  conversationId: string | null;
  target?: ChatTarget | null;
}

function isChatTarget(value: unknown): value is ChatTarget {
  return typeof value === "string" && (CHAT_TARGETS as readonly string[]).includes(value);
}

export function parseStoredTestChat(raw: string | null): StoredTestChat | null {
  if (!raw) {
    return null;
  }
  try {
    const value = JSON.parse(raw) as Partial<StoredTestChat>;
    if (!isSessionKey(value.sessionKey)) {
      return null;
    }
    return {
      sessionKey: value.sessionKey,
      versionId: typeof value.versionId === "string" ? value.versionId : null,
      conversationId: typeof value.conversationId === "string" ? value.conversationId : null,
      target: isChatTarget(value.target) ? value.target : null,
    };
  } catch {
    return null;
  }
}

/** Messages shown in the chat: customer and assistant lines (system notes too). */
export function chatMessages(messages: readonly MessageView[]): MessageView[] {
  return [...messages].sort((left, right) => left.created_at - right.created_at);
}
