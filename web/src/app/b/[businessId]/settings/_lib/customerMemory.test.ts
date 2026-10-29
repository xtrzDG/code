import { describe, expect, it } from "vitest";

import { canShareNotes, memoryBody, memoryChangeText, memorySwitches } from "./customerMemory";

const ON = { remembersCustomers: true, sharesTeamNotes: false };

describe("customer memory switches", () => {
  it("reads the stored settings", () => {
    expect(memorySwitches({ remembers_customers: false, shares_team_notes: true, updated_at: null })).toEqual({
      remembersCustomers: false,
      sharesTeamNotes: true,
    });
  });

  it("saves both switches with one of them changed", () => {
    expect(memoryBody(ON, { sharesTeamNotes: true })).toEqual({ remembers_customers: true, shares_team_notes: true });
    expect(memoryBody(ON, { remembersCustomers: false })).toEqual({ remembers_customers: false, shares_team_notes: false });
  });

  it("tells the owner what changed", () => {
    expect(memoryChangeText(ON, { ...ON, remembersCustomers: false })).toBe("customerMemory.turnedOff");
    expect(memoryChangeText({ ...ON, remembersCustomers: false }, ON)).toBe("customerMemory.turnedOn");
    expect(memoryChangeText(ON, { ...ON, sharesTeamNotes: true })).toBe("customerMemory.notesShared");
    expect(memoryChangeText({ ...ON, sharesTeamNotes: true }, ON)).toBe("customerMemory.notesHidden");
    expect(memoryChangeText(ON, ON)).toBeNull();
  });

  it("lets only owners share notes, and only while the memory is on", () => {
    expect(canShareNotes(ON, true)).toBe(true);
    expect(canShareNotes(ON, false)).toBe(false);
    expect(canShareNotes({ ...ON, remembersCustomers: false }, true)).toBe(false);
  });
});
