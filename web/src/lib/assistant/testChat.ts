/** Pure helpers of the Assistant section's test chat: sessions kept in the browser and messages. */

import type { Schema } from "@/api/types";

export type MessageView = Schema<"MessageView">;

/** A test chat session key the API accepts: ^[A-Za-z0-9][A-Za-z0-9_-]*$, at most 64. */
export function newSessionKey(now: number = Date.now(), random: () => number = Math.random): string {
  const suffix = Math.floor(random() * 36 ** 6)
    .toString(36)
    .padStart(6, "0");
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

/** The test chat remembered in the browser tab, so a reload keeps the conversation. */
export interface StoredTestChat {
  sessionKey: string;
  versionId: string | null;
  conversationId: string | null;
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
    };
  } catch {
    return null;
  }
}

/** Messages shown in the chat: customer and assistant lines (system notes too). */
export function chatMessages(messages: readonly MessageView[]): MessageView[] {
  return [...messages].sort((left, right) => left.created_at - right.created_at);
}
