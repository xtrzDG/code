/** Pure helpers of /admin/partners: the forms' checks and bodies, the payout months. */

import type { RequestBody } from "@/api/types";
import { isPayoutMonth, percentToBasisPoints, previousMonth, utcMonth } from "@/lib/referrals/referralLinks";

type PartnerContactBy = "phone" | "email";

export interface PartnerForm {
  name: string;
  by: PartnerContactBy;
  contact: string;
  ratePercent: string;
  code: string;
}

export type PartnerFormProblem = "nameRequired" | "contactRequired" | "rateInvalid" | "codeInvalid";

/** A referral code as the API accepts it (ReferralCode). */
const CODE = /^[A-Za-z0-9._-]{1,64}$/;

export function isReferralCode(code: string): boolean {
  return CODE.test(code.trim());
}

/** The first problem of the form, or null when it can be sent. */
export function partnerFormProblem(form: PartnerForm): PartnerFormProblem | null {
  if (form.name.trim() === "") {
    return "nameRequired";
  }
  if (form.contact.trim() === "") {
    return "contactRequired";
  }
  if (percentToBasisPoints(form.ratePercent) === null) {
    return "rateInvalid";
  }
  return isReferralCode(form.code) ? null : "codeInvalid";
}

/** The POST /v1/admin/partners body of a valid form. */
export function createPartnerBody(form: PartnerForm): RequestBody<"/v1/admin/partners", "post"> {
  const contact = form.contact.trim();
  return {
    name: form.name.trim(),
    ...(form.by === "phone" ? { phone_number: contact } : { email: contact }),
    commission_rate_basis_points: percentToBasisPoints(form.ratePercent) ?? 0,
    code: form.code.trim(),
  };
}

/** The payout months an admin picks from: this UTC month and the eleven before it. */
export function payoutMonths(now: Date, count = 12): string[] {
  const months = [utcMonth(now)];
  while (months.length < count) {
    months.push(previousMonth(months[months.length - 1] ?? utcMonth(now)));
  }
  return months.filter(isPayoutMonth);
}
