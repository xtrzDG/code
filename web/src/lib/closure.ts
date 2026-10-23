/**
 * Closing a business and deleting an account, as the cabinet shows them:
 * the countdown of a closing business (the banner over its cabinet and
 * Settings → Business) and the names a refused account deletion is about
 * (`DELETE /v1/me` answers 409 with the ids of the businesses or brands
 * the person is the last owner of).
 */

import type { ApiErrorReason } from "@/api/errors";
import type { BusinessClosureView, UserMembershipView } from "@/api/types";

const DAY_MS = 24 * 60 * 60 * 1000;

/** Reason codes of a refused `DELETE /v1/me`. */
export const LAST_BUSINESS_OWNER = "last_business_owner";
export const LAST_BRAND_OWNER = "last_brand_owner";
export const PLATFORM_TEAM = "platform_team";

/** Whole days until the deletion, rounded up; 0 once it is due. */
export function daysUntilDeletion(deleteAfter: number, nowMs: number): number {
  return Math.max(0, Math.ceil((deleteAfter / 1000 - nowMs) / DAY_MS));
}

export interface ClosureCountdown {
  /** When the business is deleted for good (API microseconds). */
  deleteAfter: number;
  requestedAt: number;
  daysLeft: number;
  /** Closed for non-payment: kept only once the subscription is paid again. */
  isUnpaid: boolean;
  /** The viewer may keep the business now (an owner; paid again if it was unpaid). */
  canCancel: boolean;
  /** Who closed it; null when the platform did (non-payment). */
  actorName: string | null;
}

/** A closing business's countdown; null when it is not closing (open, or already being deleted). */
export function closureCountdown(view: BusinessClosureView | undefined, nowMs: number): ClosureCountdown | null {
  if (view?.state !== "pending_deletion" || view.delete_after == null || view.requested_at == null) {
    return null;
  }
  return {
    deleteAfter: view.delete_after,
    requestedAt: view.requested_at,
    daysLeft: daysUntilDeletion(view.delete_after, nowMs),
    isUnpaid: view.reason === "unpaid_subscription",
    canCancel: view.can_cancel ?? false,
    actorName: view.actor_name ?? null,
  };
}

/**
 * The names of the businesses or brands a refusal names, from the person's
 * memberships (a brand by the name its locations carry); ids the person no
 * longer sees are left out.
 */
export function refusedNames(reason: ApiErrorReason, memberships: readonly UserMembershipView[]): string[] {
  const names = new Map<string, string>();
  for (const membership of memberships) {
    if (reason.code === LAST_BUSINESS_OWNER) {
      names.set(membership.business_id, membership.business_name);
    } else if (membership.brand_id && membership.brand_name) {
      names.set(membership.brand_id, membership.brand_name);
    }
  }
  return [...new Set(reason.details.flatMap((id) => names.get(id) ?? []))];
}
