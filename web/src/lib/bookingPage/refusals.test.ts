import { describe, expect, it } from "vitest";

import { ApiError } from "@/api/errors";

import { isBookingPagePath, withoutBookingToken } from "./paths";
import { bookingProblem, isPageProblem } from "./refusals";

function refusal(status: number, code: string): ApiError {
  return new ApiError({
    status,
    code: status === 404 ? "not_found" : status === 409 ? "conflict" : "validation_failed",
    reasons: [{ code, message: "", details: [] }],
  });
}

describe("bookingProblem", () => {
  it.each([
    [404, "link_invalid", "linkInvalid"],
    [404, "link_expired", "linkExpired"],
    [404, "booking_changed", "bookingChanged"],
    [409, "not_active", "notActive"],
    [409, "already_started", "alreadyStarted"],
    [409, "taken", "taken"],
    [422, "too_soon", "taken"],
    [422, "closed", "closedTime"],
  ])("reads %s %s as %s", (status, code, problem) => {
    expect(bookingProblem(refusal(status, code))).toBe(problem);
  });

  it("reads the status when no reason is known", () => {
    expect(bookingProblem(new ApiError({ status: 429, code: "rate_limited" }))).toBe("tooMany");
    expect(bookingProblem(new ApiError({ status: 404, code: "not_found" }))).toBe("linkInvalid");
    expect(bookingProblem(new ApiError({ status: 500, code: "internal_error" }))).toBe("generic");
    expect(bookingProblem(new TypeError("Failed to fetch"))).toBe("generic");
  });

  it("knows which problems leave no booking to show", () => {
    expect(isPageProblem("bookingChanged")).toBe(true);
    expect(isPageProblem("linkExpired")).toBe(true);
    expect(isPageProblem("taken")).toBe(false);
  });
});

describe("booking page paths", () => {
  it("recognises the page and masks its key", () => {
    expect(isBookingPagePath("/r/AbC123")).toBe(true);
    expect(isBookingPagePath("/reviews")).toBe(false);
    expect(withoutBookingToken("/r/AbC-123_x?from=chat")).toBe("/r/[token]?from=chat");
    expect(withoutBookingToken("POST /v1/public/bookings/AbC-123/cancel")).toBe(
      "POST /v1/public/bookings/[token]/cancel",
    );
  });
});
