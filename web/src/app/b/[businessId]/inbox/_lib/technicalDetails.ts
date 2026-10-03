/**
 * Whether "Technical details" under a message start open. Platform admins
 * see them open on a wide screen (lg and up), where they sit beside the
 * transcript; below that the raw requests would push the conversation
 * away, so they start closed. Whoever opens or closes them, the choice is
 * remembered per person in this browser and wins from then on.
 *
 * Storage can be missing or refuse (private windows): every access is
 * wrapped, and nothing remembered means the default.
 */

export const TECHNICAL_DETAILS_PREFIX = "aw.technicalDetails:";

/** Tailwind's lg: from here the details may start open. */
export const TECHNICAL_DETAILS_WIDE_QUERY = "(min-width: 64rem)";

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

export function startsOpen(choice: DetailsChoice | null, isPlatformAdmin: boolean, isWide: boolean): boolean {
  return choice === null ? isPlatformAdmin && isWide : choice === "open";
}

export function localChoiceStorage(): ChoiceStorage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}
