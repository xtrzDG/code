/** The lines of the test chat: what was sent, what the assistant answered, and notes. */

import type { ApiError } from "@/api/errors";
import type { Schema } from "@/api/types";
import type { MessageView } from "@/lib/assistant/testChat";

type AssistantReply = Schema<"AssistantReply">;
export type ToolCallView = Schema<"ToolCallView">;

export type ChatEntry =
  | { kind: "customer"; key: string; text: string; status: "sending" | "sent" | "failed"; error?: ApiError }
  | {
      kind: "assistant";
      key: string;
      text: string;
      reply?: AssistantReply;
      toolCalls?: ToolCallView[];
      /** The options the answer offered to tap (offer_choices), as the customer sees them. */
      choices?: readonly string[];
      /** The version that answered (from the reply, or the restored conversation). */
      versionId: string | null;
      versionNumber?: number | null;
    }
  | { kind: "silent"; key: string }
  | { kind: "note"; key: string; author: "staff" | "system"; text: string };

/** The lines of a restored conversation, oldest first. */
export function entriesFromMessages(messages: readonly MessageView[], versionId: string | null): ChatEntry[] {
  return [...messages]
    .sort((left, right) => left.created_at - right.created_at)
    .map((message): ChatEntry => {
      if (message.author === "customer") {
        return { kind: "customer", key: message.id, text: message.text, status: "sent" };
      }
      if (message.author === "assistant") {
        return {
          kind: "assistant",
          key: message.id,
          text: message.text,
          toolCalls: message.tool_calls ?? [],
          choices: message.choices ?? [],
          versionId,
        };
      }
      return { kind: "note", key: message.id, author: message.author, text: message.text };
    });
}

/**
 * The options to tap now: those of the last answer, while nothing came
 * after it. Once the customer writes (or taps), the earlier options are
 * history, as on a phone.
 */
export function tappableChoices(entries: readonly ChatEntry[]): { key: string; choices: readonly string[] } | null {
  const last = entries.at(-1);
  if (last?.kind !== "assistant" || (last.choices ?? []).length === 0) {
    return null;
  }
  return { key: last.key, choices: last.choices ?? [] };
}
