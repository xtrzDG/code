/**
 * Whether "Technical details" under a message start open: closed for
 * everyone (platform admins too), so raw requests never push the
 * conversation away; a person who opens or closes them has the choice
 * remembered in this browser, and it wins from then on.
 *
 * Storage can be missing or refuse (private windows): every access is
 * wrapped, and nothing remembered means the default.
 */

const TECHNICAL_DETAILS_PREFIX = "aw.technicalDetails:";

export type DetailsChoice = "open" | "closed";

export type ChoiceStorage = Pick<Storage, "getItem" | "setItem">;

export function readDetailsChoice(storage: ChoiceStorage | null, userId: string): DetailsChoice | null {
  try {
    const value = storage?.getItem(`${TECHNICAL_DETAILS_PREFIX}${userId}`);
    return value === "open" || value === "closed" ? value : null;
  } catch {
    return null;
  }
}

export function writeDetailsChoice(storage: ChoiceStorage | null, userId: string, choice: DetailsChoice): void {
  try {
    storage?.setItem(`${TECHNICAL_DETAILS_PREFIX}${userId}`, choice);
  } catch {
    // Not remembered: the default applies next time.
  }
}

export function startsOpen(choice: DetailsChoice | null): boolean {
  return choice === "open";
}

export function localChoiceStorage(): ChoiceStorage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}
