import { describe, expect, it } from "vitest";

import { NOTE_MAX, cleanNote, isNoteEdited, isNoteValid } from "./clientNotes";

describe("client notes", () => {
  it("takes 1 to 2,000 characters, sent without blanks around them", () => {
    expect(isNoteValid("   ")).toBe(false);
    expect(isNoteValid("Prefers WhatsApp, not calls")).toBe(true);
    expect(isNoteValid("x".repeat(NOTE_MAX))).toBe(true);
    expect(isNoteValid("x".repeat(NOTE_MAX + 1))).toBe(false);
    expect(cleanNote("\n Call after 18:00 \n")).toBe("Call after 18:00");
  });

  it("counts a note as edited only when it changed after it was written", () => {
    expect(isNoteEdited({ created_at: 1_000_000, updated_at: 1_000_000 })).toBe(false);
    expect(isNoteEdited({ created_at: 1_000_000, updated_at: 1_500_000 })).toBe(false);
    expect(isNoteEdited({ created_at: 1_000_000, updated_at: 90_000_000 })).toBe(true);
  });
});
