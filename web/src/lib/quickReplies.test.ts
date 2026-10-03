import { describe, expect, it } from "vitest";

import {
  fillPlaceholder,
  insertAt,
  isValidShortcut,
  placeholderOf,
  placeholdersIn,
  previewQuickReply,
  SHORTCUT_MAX_LENGTH,
} from "./quickReplies";

describe("a quick reply's shortcut", () => {
  it("is letters of any script, digits, _ and -, up to its length", () => {
    expect(isValidShortcut("hours")).toBe(true);
    expect(isValidShortcut("მაგიდა")).toBe(true);
    expect(isValidShortcut("стол_2-й")).toBe(true);
    expect(isValidShortcut("")).toBe(false);
    expect(isValidShortcut("two words")).toBe(false);
    expect(isValidShortcut("/hours")).toBe(false);
    expect(isValidShortcut("x".repeat(SHORTCUT_MAX_LENGTH + 1))).toBe(false);
  });
});

describe("the variables of a text", () => {
  it("are the known names in braces, each once, in order", () => {
    expect(placeholderOf("booking_time")).toBe("{booking_time}");
    expect(placeholdersIn("{name}, your table at {business_name} is at {booking_time}. {name}!")).toEqual([
      "name",
      "business_name",
      "booking_time",
    ]);
    expect(placeholdersIn("A {discount} for {name}")).toEqual(["name"]);
  });

  it("are filled everywhere, and an empty value leaves them", () => {
    expect(fillPlaceholder("{name}, see you, {name}", "name", " Nino ")).toBe("Nino, see you, Nino");
    expect(fillPlaceholder("{name}", "name", "  ")).toBe("{name}");
  });

  it("read as a customer would see them in the preview", () => {
    expect(
      previewQuickReply("{name}: {business_name} at {booking_time}", {
        name: "Nino",
        booking_time: "Fri 19:00",
        business_name: "Salobie",
      }),
    ).toBe("Nino: Salobie at Fri 19:00");
  });
});

describe("inserting at the caret", () => {
  it("puts the text at the caret or in place of the selection", () => {
    expect(insertAt("Hello !", "{name}", 6)).toEqual({ text: "Hello {name}!", caret: 12 });
    expect(insertAt("Hello you!", "{name}", 6, 9)).toEqual({ text: "Hello {name}!", caret: 12 });
    expect(insertAt("Hi", "{name}", 99)).toEqual({ text: "Hi{name}", caret: 8 });
  });
});
