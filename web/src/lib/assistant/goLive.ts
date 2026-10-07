/**
 * Pure helpers of going live: the go-live checklist and publish or rollback
 * refusals, by the API's reason codes.
 */

import type { ApiError } from "@/api/errors";
import type { Schema } from "@/api/types";

export type GoLiveCheckCode = Schema<"GoLiveCheckCode">;
export type GoLiveCheck = Schema<"GoLiveCheck">;
export type GoLiveReadiness = Schema<"GoLiveReadiness">;

/** Checklist codes, in the order the API lists them. */
const GO_LIVE_CHECK_CODES: readonly GoLiveCheckCode[] = [
  "subscription_or_trial",
  "dpa",
  "profile_gaps",
  "staff_contact",
  "autotests",
  "voice_configuration",
];

/** Why a version cannot be published or rolled back in its current state. */
const VERSION_REFUSAL_CODES = [
  "version_already_live",
  "version_archived",
  "version_not_archived",
  "force_publish_admin_only",
] as const;

type VersionRefusalCode = (typeof VERSION_REFUSAL_CODES)[number];
export type RefusalCode = GoLiveCheckCode | VersionRefusalCode;

export interface Refusal {
  /** A code the cabinet knows, or null (then `message` is shown). */
  code: RefusalCode | null;
  message: string;
  details: string[];
}

const REFUSAL_CODES: ReadonlySet<string> = new Set<string>([...GO_LIVE_CHECK_CODES, ...VERSION_REFUSAL_CODES]);

function isRefusalCode(code: string): code is RefusalCode {
  return REFUSAL_CODES.has(code);
}

/**
 * Why the API refused to publish or roll back (409, or 403 for a forced
 * publish), from the machine-readable reasons of its answer. Empty for
 * other errors, or when the API named no reason.
 */
export function refusalReasons(error: Pick<ApiError, "status" | "reasons"> | null | undefined): Refusal[] {
  if (!error || (error.status !== 409 && error.status !== 403)) {
    return [];
  }
  return error.reasons.map((reason) => ({
    code: isRefusalCode(reason.code) ? reason.code : null,
    message: reason.message,
    details: [...reason.details],
  }));
}

/** True when the refusal is about a version still under test (not a missing test). */
export function isTestingRefusal(reason: Pick<Refusal, "code" | "details">): boolean {
  return reason.code === "autotests" && reason.details[0] === "testing";
}

export type CheckState = "ok" | "missing" | "warning" | "pending";

/**
 * How a checklist row looks: done, missing (stops publishing), a warning
 * (does not stop it), or in progress (the version is being tested).
 */
export function checkState(check: Pick<GoLiveCheck, "code" | "is_ok" | "is_blocking" | "details">): CheckState {
  if (check.is_ok) {
    return "ok";
  }
  if (check.code === "autotests" && (check.details ?? [])[0] === "testing") {
    return "pending";
  }
  return check.is_blocking ? "missing" : "warning";
}

/** Checks that still stop the version from going live. */
export function blockingChecks<T extends Pick<GoLiveCheck, "is_ok" | "is_blocking">>(checks: readonly T[]): T[] {
  return checks.filter((check) => !check.is_ok && check.is_blocking);
}

/** The detail of a passed billing check: the free trial starts at the first go-live. */
const TRIAL_AT_GO_LIVE_DETAIL = "trial_at_go_live";

export type BillingCheckText =
  | "assistant.checklist.billingTrialAtGoLive"
  | "assistant.checklist.billingTrial"
  | "assistant.checklist.billingActive"
  | "assistant.checklist.billingStartTrial"
  | "assistant.checklist.billingMissing";

/**
 * What the billing check of the go-live checklist says: the trial that
 * starts at go-live, the running trial or paid subscription, or what is
 * missing (no subscription at all, or one that needs paying).
 */
export function billingCheckText(
  check: Pick<GoLiveCheck, "is_ok" | "details">,
  subscriptionStatus: GoLiveReadiness["subscription_status"],
): BillingCheckText {
  const detail = (check.details ?? [])[0];
  if (check.is_ok) {
    if (detail === TRIAL_AT_GO_LIVE_DETAIL) return "assistant.checklist.billingTrialAtGoLive";
    return subscriptionStatus === "trialing" ? "assistant.checklist.billingTrial" : "assistant.checklist.billingActive";
  }
  return detail === "none" ? "assistant.checklist.billingStartTrial" : "assistant.checklist.billingMissing";
}
