/**
 * The "Phone calls" section of a hosted chat's privacy notice, when the
 * business's AI assistant answers its phone: calls are not recorded unless
 * the owner turned recording on (Settings → Calls); then the caller is told
 * (or asked, where the law wants every party's consent) and free to decline,
 * and recordings are kept for the business's period.
 */

import type { Schema } from "@/api/types";

import type { PrivacyNoticeTexts } from "./noticeTypes";

export type HostedChatPhoneCalls = Schema<"HostedChatPhoneCalls">;

export function phoneCallKeys(phone: HostedChatPhoneCalls): (keyof PrivacyNoticeTexts)[] {
  if (!phone.is_recording_enabled) {
    return ["callsNotRecorded"];
  }
  return [
    "callsRecorded",
    phone.recording_consent_rule === "all_party_consent" ? "callsConsent" : "callsNotice",
    "callsDecline",
    "callsKept",
  ];
}
