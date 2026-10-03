import type { ReasonMessages } from "@/api/errors";

/**
 * Booking refusals in the user's language, by the API's reason codes
 * (closed that day, too soon, taken, party too large, no place seats it),
 * instead of a generic title and the backend's English sentence.
 */
export const BOOKING_REFUSAL_MESSAGES: ReasonMessages = {
  closed: (reason) => ({ key: "bookings.errors.closed", values: { day: reason.details[0] ?? "" } }),
  too_soon: () => ({ key: "bookings.errors.tooSoon" }),
  time_required: () => ({ key: "bookings.errors.timeRequired" }),
  taken: (reason) => ({ key: "bookings.errors.taken", values: { day: reason.details[0] ?? "" } }),
  party_too_large: (reason) => ({ key: "bookings.errors.partyTooLarge", values: { max: reason.details[0] ?? "" } }),
  no_seating_resource: (reason) =>
    reason.details[0]
      ? { key: "bookings.errors.noSeatingResource", values: { count: reason.details[0] } }
      : { key: "bookings.errors.noSeatingResourceForParty" },
};
