import { describe, expect, it } from "vitest";

import { phoneCallKeys } from "./phoneCallKeys";
import { privacyNoticeFor } from "./privacyNoticeTexts";

describe("the phone calls of the privacy notice", () => {
  it("say calls are not recorded while the business does not record them", () => {
    const keys = phoneCallKeys({
      recording_consent_rule: "all_party_consent",
      recording_retention_days: 90,
      is_recording_enabled: false,
    });

    expect(keys).toEqual(["callsNotRecorded"]);
    expect(privacyNoticeFor("en").text("callsNotRecorded", { business: "Da Mario" })).toContain("not recorded");
    expect(privacyNoticeFor("it").text("callsNotRecorded", { business: "Da Mario" })).toContain("non viene registrata");
  });

  it("say how a recorded call is announced, by the country's rule", () => {
    expect(phoneCallKeys({ recording_consent_rule: "notice", recording_retention_days: 90, is_recording_enabled: true })).toEqual([
      "callsRecorded",
      "callsNotice",
      "callsDecline",
      "callsKept",
    ]);
    expect(
      phoneCallKeys({ recording_consent_rule: "all_party_consent", recording_retention_days: 90, is_recording_enabled: true }),
    ).toContain("callsConsent");
  });
});
