import { describe, expect, it } from "vitest";

import type { MessageView } from "@/lib/assistant/testChat";

import { entriesFromMessages, tappableChoices, type ChatEntry } from "./chatEntries";

function message(overrides: Partial<MessageView>): MessageView {
  return {
    id: "m",
    author: "customer",
    text: "",
    created_at: 1,
    ...overrides,
  } as MessageView;
}

const OFFER: ChatEntry = {
  kind: "assistant",
  key: "a1",
  text: "Which time suits you?",
  choices: ["18:00", "19:30"],
  versionId: null,
};

describe("tappableChoices", () => {
  it("offers the options of the last answer", () => {
    expect(tappableChoices([{ kind: "customer", key: "c1", text: "A table?", status: "sent" }, OFFER])).toEqual({
      key: "a1",
      choices: ["18:00", "19:30"],
    });
  });

  it("drops them once the customer writes, and without options there is nothing", () => {
    expect(tappableChoices([OFFER, { kind: "customer", key: "c2", text: "19:30", status: "sending" }])).toBeNull();
    expect(tappableChoices([{ ...OFFER, choices: [] }])).toBeNull();
    expect(tappableChoices([{ ...OFFER, choices: undefined }])).toBeNull();
    expect(tappableChoices([])).toBeNull();
  });
});

describe("entriesFromMessages", () => {
  it("restores the options an answer offered", () => {
    const entries = entriesFromMessages(
      [
        message({ id: "a", author: "assistant", text: "Which time?", choices: ["18:00"], created_at: 2 }),
        message({ id: "c", author: "customer", text: "A table?", created_at: 1 }),
        message({ id: "b", author: "assistant", text: "Done.", created_at: 3 }),
      ],
      "v1",
    );

    expect(entries.map((entry) => (entry.kind === "assistant" ? entry.choices : entry.kind))).toEqual([
      "customer",
      ["18:00"],
      [],
    ]);
  });
});
