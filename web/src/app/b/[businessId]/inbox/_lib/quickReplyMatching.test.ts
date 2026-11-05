import { describe, expect, it } from "vitest";

import { matchQuickReplies, slashQuery } from "./quickReplyMatching";
import type { FilledQuickReplyView } from "./types";

const reply = (id: string, shortcut: string, title: string, text: string): FilledQuickReplyView => ({
  id,
  shortcut,
  title,
  text,
  language: "en",
  missing_variables: [],
});

const replies = [
  reply("quick_reply_1", "hours", "Opening hours", "We are open from noon."),
  reply("quick_reply_2", "ready", "Table is ready", "Your table at the Café is ready."),
  reply("quick_reply_3", "parking", "Parking", "Park behind the house."),
];

describe("the picker command", () => {
  it("is a slash and a word, nothing else", () => {
    expect(slashQuery("/")).toBe("");
    expect(slashQuery("/hou")).toBe("hou");
    expect(slashQuery("  /მაგიდა")).toBe("მაგიდა");
    expect(slashQuery("hello /hours")).toBeNull();
    expect(slashQuery("/hours now")).toBeNull();
    expect(slashQuery("")).toBeNull();
  });
});

describe("matching quick replies", () => {
  it("lists every reply in the owner's order for an empty query", () => {
    expect(matchQuickReplies(replies, "").map((item) => item.shortcut)).toEqual(["hours", "ready", "parking"]);
  });

  it("ranks a shortcut that starts with the query before a name or text that holds it", () => {
    expect(matchQuickReplies(replies, "par").map((item) => item.shortcut)).toEqual(["parking"]);
    expect(matchQuickReplies(replies, "table").map((item) => item.shortcut)).toEqual(["ready"]);
    // "ho": the shortcut "hours" first, then "Park behind the house".
    expect(matchQuickReplies(replies, "ho").map((item) => item.shortcut)).toEqual(["hours", "parking"]);
  });

  it("ignores case and accents", () => {
    expect(matchQuickReplies(replies, "CAFE").map((item) => item.shortcut)).toEqual(["ready"]);
    expect(matchQuickReplies(replies, "nothing")).toEqual([]);
  });
});
