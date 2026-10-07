/**
 * What the after-call check of the phone assistant's spoken values found,
 * as the conversation card shows it: a calm "checked" label for a clean
 * call, and for findings a warning with the values to compare against the
 * transcript (and, when the call made a booking or request, the note that
 * a colleague got a task to check it).
 */

import type { BadgeTone } from "@/components/ui";
import type { CallGuardVerdict, CallView } from "@/components/insights/types";
import type { MessageKey } from "@/i18n/translate";

export interface CallGuardBadge {
  tone: BadgeTone;
  label: MessageKey;
}

const CALL_GUARD_BADGES: Record<CallGuardVerdict, CallGuardBadge> = {
  clean: { tone: "success", label: "conversations.calls.guard.clean" },
  flagged: { tone: "warning", label: "conversations.calls.guard.flagged" },
  handed_off: { tone: "warning", label: "conversations.calls.guard.handedOff" },
};

export interface CallGuardFindings {
  title: MessageKey;
  values: readonly string[];
}

/** The badge of a checked call; none for a call that was not checked. */
export function callGuardBadge(call: Pick<CallView, "guard_verdict">): CallGuardBadge | null {
  return call.guard_verdict ? CALL_GUARD_BADGES[call.guard_verdict] : null;
}

/** The warning of a call whose values were not all found; null when clean. */
export function callGuardFindings(
  call: Pick<CallView, "guard_verdict" | "unverified_values">,
): CallGuardFindings | null {
  const values = call.unverified_values ?? [];
  if (values.length === 0 || (call.guard_verdict !== "flagged" && call.guard_verdict !== "handed_off")) {
    return null;
  }
  return {
    title:
      call.guard_verdict === "handed_off"
        ? "conversations.calls.guard.handedOffTitle"
        : "conversations.calls.guard.flaggedTitle",
    values,
  };
}
