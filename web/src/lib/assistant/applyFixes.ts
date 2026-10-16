/**
 * Where the cabinet fixes what stopped "Apply changes": each reason of
 * GET …/assistant/apply names a place (the profile, the staff contacts,
 * the plan, the checks…); in the daily cabinet that place is a page, and
 * failed checks open the conversations that did not pass.
 */

import type { Schema } from "@/api/types";
import { businessPath, type BusinessPage } from "@/lib/navigation";

type SetupActionTarget = Schema<"SetupActionTarget">;

const FIX_PAGES: Record<SetupActionTarget, BusinessPage | null> = {
  profile: "assistant/profile",
  staff_contacts: "settings/notifications",
  channels: "assistant/channels",
  test_chat: "assistant",
  agreement: "settings/privacy",
  billing: "settings/billing",
  checks: "assistant/versions",
  overview: "overview",
  // The guide after the launch: its QR code lives on the Overview, the
  // link and QR card on the Channels page.
  phone_test: "overview",
  share: "assistant/channels",
  // "Apply changes" itself: the button is right there.
  apply_changes: null,
};

/** The checks of a version that did not pass (the version page opens on them). */
export function failedChecksPath(businessId: string, versionId: string | null | undefined): string {
  const versions = businessPath(businessId, "assistant/versions");
  return versionId ? `${versions}/${encodeURIComponent(versionId)}?checks=problems` : versions;
}

/** The page that fixes a reason, or null when there is nothing to open. */
export function fixPath(
  businessId: string,
  action: Schema<"SetupActionView">,
  versionId: string | null | undefined,
): string | null {
  if (action.target === "checks") {
    return failedChecksPath(businessId, versionId);
  }
  const page = FIX_PAGES[action.target];
  return page ? businessPath(businessId, page) : null;
}
