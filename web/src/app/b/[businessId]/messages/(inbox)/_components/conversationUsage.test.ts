import { describe, expect, it } from "vitest";

import { addUsage, fromUsage, usageTotals } from "./conversationUsage";

describe("conversation usage", () => {
  it("shows the totals the API summed over the whole conversation", () => {
    expect(
      fromUsage({
        input_tokens: 1200,
        output_tokens: 300,
        cost_micro_usd: 4100,
      }),
    ).toEqual({
      inputTokens: 1200,
      outputTokens: 300,
      costMicroUsd: 4100,
    });
    expect(fromUsage({})).toEqual({
      inputTokens: 0,
      outputTokens: 0,
      costMicroUsd: 0,
    });
  });

  it("adds a reply sent from the card", () => {
    expect(
      addUsage(
        { input_tokens: 10, output_tokens: 5, cost_micro_usd: 7 },
        {
          input_tokens: 2,
          output_tokens: 1,
          cost_micro_usd: 3,
        },
      ),
    ).toEqual({ input_tokens: 12, output_tokens: 6, cost_micro_usd: 10 });
  });

  it("falls back to the messages shown", () => {
    expect(
      usageTotals([
        { input_tokens: 1, output_tokens: 2, cost_micro_usd: 3 },
        { input_tokens: 4, output_tokens: 5, cost_micro_usd: 6 },
      ]),
    ).toEqual({ inputTokens: 5, outputTokens: 7, costMicroUsd: 9 });
  });
});
