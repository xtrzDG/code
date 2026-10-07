/**
 * Why a guest's booking page could not do what was asked, as the key of
 * its text (texts.ts): the API's refusal reasons (ManagedBookingRefusalCode
 * and the booking refusals of a move), else what the status says.
 */

import { isApiError } from "@/api/errors";

import type { BookingPageTexts } from "./texts";

export type BookingProblem = keyof Pick<
  BookingPageTexts,
  | "linkInvalid"
  | "linkExpired"
  | "bookingChanged"
  | "notActive"
  | "alreadyStarted"
  | "taken"
  | "closedTime"
  | "tooMany"
  | "generic"
>;

const REASON_PROBLEMS: Readonly<Record<string, BookingProblem>> = {
  link_invalid: "linkInvalid",
  link_expired: "linkExpired",
  booking_changed: "bookingChanged",
  not_active: "notActive",
  already_started: "alreadyStarted",
  taken: "taken",
  too_soon: "taken",
  closed: "closedTime",
};

/** Problems that leave nothing to show: the page is the explanation. */
const PAGE_PROBLEMS: ReadonlySet<BookingProblem> = new Set(["linkInvalid", "linkExpired", "bookingChanged"]);

export function bookingProblem(error: unknown): BookingProblem {
  if (!isApiError(error)) {
    return "generic";
  }
  for (const reason of error.reasons) {
    const problem = REASON_PROBLEMS[reason.code];
    if (problem) {
      return problem;
    }
  }
  if (error.status === 429) {
    return "tooMany";
  }
  return error.status === 404 ? "linkInvalid" : "generic";
}

/** True when the booking itself can no longer be shown through this link. */
export function isPageProblem(problem: BookingProblem): boolean {
  return PAGE_PROBLEMS.has(problem);
}
