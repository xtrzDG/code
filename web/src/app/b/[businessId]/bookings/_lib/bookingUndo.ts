/**
 * Undoing a status change (POST …/bookings/{id}/revert-status): the API's
 * refusal reasons in the user's language. The API keeps the change it may
 * undo for 10 minutes, so the toast's Undo always finds it in time; a
 * refusal means someone else acted in the meantime.
 */

import type { ReasonMessages } from "@/api/errors";

export const UNDO_REFUSAL_MESSAGES: ReasonMessages = {
  slot_taken: () => ({ key: "bookings.undo.slotTaken" }),
  undo_expired: (reason) => {
    const minutes = reason.details[0] ?? "10";
    return { pluralKey: "bookings.undo.expired", count: Number(minutes), values: { minutes } };
  },
  nothing_to_undo: () => ({ key: "bookings.undo.changed" }),
  status_changed: () => ({ key: "bookings.undo.changed" }),
  place_gone: () => ({ key: "bookings.undo.placeGone" }),
};
