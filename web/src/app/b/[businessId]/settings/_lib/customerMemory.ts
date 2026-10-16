/**
 * Settings → General's customer memory: the stored switches, the body a
 * change saves and what the owner is told after it.
 */

import type { RequestBody, Schema } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";

export type AssistantSettingsView = Schema<"AssistantSettingsView">;
export type AssistantSettingsBody = RequestBody<"/v1/businesses/{business_id}/assistant-settings", "put">;

export interface MemorySwitches {
  remembersCustomers: boolean;
  sharesTeamNotes: boolean;
}

export function memorySwitches(view: AssistantSettingsView): MemorySwitches {
  return { remembersCustomers: view.remembers_customers, sharesTeamNotes: view.shares_team_notes };
}

/** The whole settings with one switch changed (a PUT replaces both). */
export function memoryBody(current: MemorySwitches, change: Partial<MemorySwitches>): AssistantSettingsBody {
  const next = { ...current, ...change };
  return { remembers_customers: next.remembersCustomers, shares_team_notes: next.sharesTeamNotes };
}

/** The toast after a saved change: what is different now. */
export function memoryChangeText(before: MemorySwitches, after: MemorySwitches): MessageKey | null {
  if (before.remembersCustomers !== after.remembersCustomers) {
    return after.remembersCustomers ? "customerMemory.turnedOn" : "customerMemory.turnedOff";
  }
  if (before.sharesTeamNotes !== after.sharesTeamNotes) {
    return after.sharesTeamNotes ? "customerMemory.notesShared" : "customerMemory.notesHidden";
  }
  return null;
}

/** The team's notes reach the memory only while there is a memory. */
export function canShareNotes(switches: MemorySwitches, isOwner: boolean): boolean {
  return isOwner && switches.remembersCustomers;
}
