import type { Schema } from "@/api/types";

export type ClientGuardActivity = Schema<"ClientGuardActivity">;

/** The API's GUARD_SPIKE rule (app/utilities/client_health/guard_activity.py). */
export const MIN_HELD_BACK_REPLIES = 5;
export const HELD_BACK_SHARE = 1 / 6;
export const INJECTION_FLAG_SPIKE = 10;

export interface GuardFigures {
  checked: number;
  heldBack: number;
  rewritten: number;
  handedOff: number;
  injectionFlags: number;
  /** Share of checked replies the guard held back, 0..1; null without checked replies. */
  heldBackShare: number | null;
}

/** The guard's work of the window, with the share of held-back replies. */
export function guardFigures(activity: ClientGuardActivity | undefined): GuardFigures {
  const checked = activity?.checked_replies ?? 0;
  const rewritten = activity?.rewritten_replies ?? 0;
  const handedOff = activity?.handed_off_replies ?? 0;
  const heldBack = rewritten + handedOff;
  return {
    checked,
    heldBack,
    rewritten,
    handedOff,
    injectionFlags: activity?.injection_flags ?? 0,
    heldBackShare: checked > 0 ? heldBack / checked : null,
  };
}

/** Whether the replies held back are a pattern (at least five, one in six). */
export function isHeldBackOften(figures: GuardFigures): boolean {
  return figures.heldBack >= MIN_HELD_BACK_REPLIES && (figures.heldBackShare ?? 0) >= HELD_BACK_SHARE;
}

/** Whether the injection attempts are a pattern (ten in the window). */
export function isProbed(figures: GuardFigures): boolean {
  return figures.injectionFlags >= INJECTION_FLAG_SPIKE;
}
