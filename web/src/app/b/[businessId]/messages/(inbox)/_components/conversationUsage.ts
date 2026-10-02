/** Model usage of a conversation as the card shows it. */

import type { ConversationUsageView, MessageView } from "@/components/insights/types";

type MessageUsage = Pick<MessageView, "input_tokens" | "output_tokens" | "cost_micro_usd">;

export interface UsageTotals {
  inputTokens: number;
  outputTokens: number;
  costMicroUsd: number;
}

/** The card's totals from the usage the API sums over the whole conversation. */
export function fromUsage(usage: ConversationUsageView): UsageTotals {
  return {
    inputTokens: usage.input_tokens ?? 0,
    outputTokens: usage.output_tokens ?? 0,
    costMicroUsd: usage.cost_micro_usd ?? 0,
  };
}

/** The usage after one more message (a staff reply sent from the card). */
export function addUsage(
  usage: ConversationUsageView,
  message: MessageUsage,
): ConversationUsageView {
  return {
    input_tokens: (usage.input_tokens ?? 0) + message.input_tokens,
    output_tokens: (usage.output_tokens ?? 0) + message.output_tokens,
    cost_micro_usd: (usage.cost_micro_usd ?? 0) + message.cost_micro_usd,
  };
}

/** Totals of the messages shown (before the API sums the whole conversation). */
export function usageTotals(messages: readonly MessageUsage[]): UsageTotals {
  return messages.reduce<UsageTotals>(
    (totals, message) => ({
      inputTokens: totals.inputTokens + message.input_tokens,
      outputTokens: totals.outputTokens + message.output_tokens,
      costMicroUsd: totals.costMicroUsd + message.cost_micro_usd,
    }),
    { inputTokens: 0, outputTokens: 0, costMicroUsd: 0 },
  );
}
