/**
 * Texts of the referral program: an owner's invitation and "Powered by"
 * link, the partner portal (/partner) and the platform admin's partners
 * and payouts (/admin/partners).
 *
 * Top-level keys are namespaces. They are spread into the dictionaries of
 * every locale, so they must not clash with the namespaces of the other
 * dictionaries. The other languages are type-checked against `en`.
 *
 * Each namespace lives in its own file per language under `./referrals/`;
 * this file composes them.
 */

import type { Translation } from "../../translate";
import { adminPartnersEn } from "./referrals/adminPartners.en";
import { partnerPortalEn } from "./referrals/partnerPortal.en";
import { referralsEn } from "./referrals/referrals.en";
import { adminPartnersIt } from "./referrals/adminPartners.it";
import { partnerPortalIt } from "./referrals/partnerPortal.it";
import { referralsIt } from "./referrals/referrals.it";

export const referralsSectionEn = {
  referrals: referralsEn,
  partnerPortal: partnerPortalEn,
  adminPartners: adminPartnersEn,
} as const;

export const referralsSectionIt: Translation<typeof referralsSectionEn> = {
  referrals: referralsIt,
  partnerPortal: partnerPortalIt,
  adminPartners: adminPartnersIt,
};
