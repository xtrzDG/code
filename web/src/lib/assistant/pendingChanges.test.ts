import { describe, expect, it } from "vitest";

import { en } from "@/i18n/messages/en";
import { ka } from "@/i18n/messages/ka";
import { ru } from "@/i18n/messages/ru";
import { createTranslator } from "@/i18n/translate";

import {
  describeChange,
  formatPrice,
  groupChanges,
  summarizeChanges,
  touchesPendingChanges,
  type PendingChange,
} from "./pendingChanges";
import { failedChecksPath, fixPath } from "./applyFixes";

const english = createTranslator("en", en);
const russian = createTranslator("ru", ru, en);
const georgian = createTranslator("ka", ka, en);

const priceChange: PendingChange = {
  area: "offer",
  action: "changed",
  detail: "price",
  item_kind: "menu_item",
  subject: "Khachapuri",
  before: "18.00 GEL",
  after: "20.00 GEL",
};

describe("pending changes in the owner's words", () => {
  it("write prices the way the locale writes money", () => {
    expect(formatPrice("18.00 GEL", "en")).toContain("18.00");
    expect(formatPrice("18.00 GEL", "ru")).toContain("18,00");
    expect(formatPrice("from 18 GEL", "en")).toBe("from 18 GEL");
    expect(formatPrice(null, "en")).toBe("");
  });

  it("name a new price with its item, before and after", () => {
    const line = describeChange(priceChange, english);
    expect(line).toMatch(/^Price of “Khachapuri”: .*18\.00.* → .*20\.00/);
    expect(describeChange(priceChange, russian)).toMatch(/^Цена «Khachapuri»: /);
    expect(describeChange({ ...priceChange, before: null }, english)).toMatch(/^Price of “Khachapuri”: .*20\.00/);
    expect(describeChange({ ...priceChange, after: null }, english)).toBe("Price of “Khachapuri” removed");
    expect(describeChange({ ...priceChange, detail: "details" }, english)).toBe("Details of “Khachapuri” changed");
  });

  it("say what was added, changed or removed in each area", () => {
    const cases: [PendingChange, string][] = [
      [{ area: "offer", action: "added", subject: "Lobio" }, "Added: “Lobio”"],
      [{ area: "questions", action: "removed", subject: "Parking?" }, "Removed: “Parking?”"],
      [{ area: "resources", action: "changed", subject: "Table 4" }, "Changed: “Table 4”"],
      [{ area: "answers", action: "changed", subject: "Do you deliver?" }, "Changed: “Do you deliver?”"],
      [{ area: "profile", action: "changed", field: "address" }, "Changed: address"],
      [{ area: "booking_rules", action: "added", field: "booking_deposit" }, "Added: deposit"],
      [{ area: "languages", action: "changed", field: "default_language" }, "Changed: main language"],
      [{ area: "links", action: "added", link_kind: "menu" }, "Added: menu link"],
      [{ area: "hours", action: "changed", weekday: 1 }, "Changed: opening hours (Monday)"],
      [{ area: "calls", action: "added" }, "The assistant now answers phone calls"],
      [{ area: "conversation", action: "changed" }, en.applyChanges.conversation],
    ];
    for (const [change, text] of cases) {
      expect(describeChange(change, english)).toBe(text);
    }
    expect(describeChange({ area: "special_days", action: "added", date: "2026-12-31" }, english)).toBe(
      "Added: special day December 31, 2026",
    );
  });

  it("have every text in Russian and Georgian", () => {
    const change: PendingChange = { area: "profile", action: "changed", field: "public_phone" };
    expect(describeChange(change, russian)).toBe("Изменено: телефон для клиентов");
    expect(describeChange(change, georgian)).not.toContain("applyChanges");
    expect(describeChange({ area: "links", action: "removed", link_kind: "google_review" }, georgian)).not.toContain("applyChanges");
  });

  it("group the changes by area in a fixed order", () => {
    const groups = groupChanges([
      { area: "offer", action: "added", subject: "Lobio" },
      { area: "profile", action: "changed", field: "city" },
      { area: "offer", action: "removed", subject: "Pkhali" },
    ]);
    expect(groups.map((group) => group.area)).toEqual(["profile", "offer"]);
    expect(groups[1]?.changes).toHaveLength(2);
  });

  it("sum up what the assistant now knows for the toast", () => {
    expect(summarizeChanges([priceChange], english)).toMatch(/^Your assistant now knows: “Khachapuri”, .*20\.00/);
    expect(summarizeChanges([priceChange], russian)).toMatch(/^Теперь помощник знает: «Khachapuri» — .*20,00/);
    const many: PendingChange[] = ["A", "B", "C", "D", "E"].map((subject) => ({ area: "offer", action: "added", subject }));
    expect(summarizeChanges(many, english)).toBe("Your assistant now knows: “A”, “B”, “C” and 2 more changes");
    expect(summarizeChanges([{ area: "offer", action: "removed", subject: "A" }], english)).toBeNull();
  });

  it("keep a line readable when the API leaves a detail out", () => {
    expect(describeChange({ area: "special_days", action: "removed", date: null }, english)).toBe("Removed: special day ");
    expect(describeChange({ area: "hours", action: "added" }, english)).toBe("Added: opening hours ()");
    expect(describeChange({ area: "links", action: "added" }, english)).toBe("Added: ");
    expect(describeChange({ area: "profile", action: "changed" }, english)).toBe("Changed: ");
    expect(describeChange({ area: "offer", action: "added" }, english)).toBe("Added: “”");
    expect(describeChange({ area: "calls", action: "removed" }, english)).toBe("The assistant no longer answers phone calls");
  });

  it("read the changes again when a source section of the same business changes", () => {
    expect(touchesPendingChanges(["knowledge", "b1"], "b1")).toBe(true);
    expect(touchesPendingChanges(["business", "b1", "detail"], "b1")).toBe(true);
    expect(touchesPendingChanges(["resources"], "b1")).toBe(true);
    expect(touchesPendingChanges(["knowledge", "b2"], "b1")).toBe(false);
    expect(touchesPendingChanges(["conversations", "b1"], "b1")).toBe(false);
    expect(touchesPendingChanges([], "b1")).toBe(false);
  });
});

describe("where a stopped Apply changes is fixed", () => {
  const action = (target: Parameters<typeof fixPath>[1]["target"]) => ({ target, label: "Fix" });

  it("open the cabinet page of each reason", () => {
    expect(fixPath("b1", action("profile"), null)).toBe("/b/b1/assistant/profile");
    expect(fixPath("b1", action("staff_contacts"), null)).toBe("/b/b1/settings/notifications");
    expect(fixPath("b1", action("billing"), null)).toBe("/b/b1/settings/billing");
    expect(fixPath("b1", action("agreement"), null)).toBe("/b/b1/settings/privacy");
    expect(fixPath("b1", action("apply_changes"), null)).toBeNull();
  });

  it("open the conversations that did not pass", () => {
    expect(fixPath("b1", action("checks"), "assistant_version_7")).toBe(
      "/b/b1/assistant/versions/assistant_version_7?checks=problems",
    );
    expect(failedChecksPath("b1", null)).toBe("/b/b1/assistant/versions");
  });
});
