import { describe, expect, it } from "vitest";

import { ApiError } from "@/api/errors";

import { metaRefusalKey } from "./metaRefusals";

const refusal = (status: number, code: string) =>
  new ApiError({
    status,
    code: status === 409 ? "conflict" : "validation_failed",
    detail: "English detail",
    reasons: [{ code, message: "English", details: [] }],
  });

describe("a Facebook sign-in refusal", () => {
  it("is named in the owner's words when the API gave its reason", () => {
    expect(metaRefusalKey(refusal(422, "meta_link_expired"))).toBe("metaConnect.refusals.meta_link_expired");
    expect(metaRefusalKey(refusal(409, "whatsapp_pin_mismatch"))).toBe("metaConnect.refusals.whatsapp_pin_mismatch");
    expect(metaRefusalKey(refusal(422, "instagram_account_missing"))).toBe("metaConnect.refusals.instagram_account_missing");
  });

  it("leaves any other failure to the general error texts", () => {
    expect(metaRefusalKey(refusal(422, "step_up_required"))).toBeNull();
    expect(metaRefusalKey(new TypeError("offline"))).toBeNull();
    expect(metaRefusalKey(null)).toBeNull();
  });
});
