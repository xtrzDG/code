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
import { adminPartnersKa } from "./referrals/adminPartners.ka";
import { adminPartnersRu } from "./referrals/adminPartners.ru";
import { partnerPortalEn } from "./referrals/partnerPortal.en";
import { partnerPortalKa } from "./referrals/partnerPortal.ka";
import { partnerPortalRu } from "./referrals/partnerPortal.ru";
import { referralsEn } from "./referrals/referrals.en";
import { referralsKa } from "./referrals/referrals.ka";
import { referralsRu } from "./referrals/referrals.ru";
import { adminPartnersHe } from "./referrals/adminPartners.he";
import { adminPartnersDe } from "./referrals/adminPartners.de";
import { partnerPortalHe } from "./referrals/partnerPortal.he";
import { partnerPortalDe } from "./referrals/partnerPortal.de";
import { referralsHe } from "./referrals/referrals.he";
import { referralsDe } from "./referrals/referrals.de";

export const referralsSectionEn = {
  referrals: referralsEn,
  partnerPortal: partnerPortalEn,
  adminPartners: adminPartnersEn,
} as const;

export const referralsSectionRu: Translation<typeof referralsSectionEn> = {
  referrals: referralsRu,
  partnerPortal: partnerPortalRu,
  adminPartners: adminPartnersRu,
};

export const referralsSectionKa: Translation<typeof referralsSectionEn> = {
  referrals: referralsKa,
  partnerPortal: partnerPortalKa,
  adminPartners: adminPartnersKa,
};

export const referralsSectionHe: Translation<typeof referralsSectionEn> = {
  referrals: referralsHe,
  partnerPortal: partnerPortalHe,
  adminPartners: adminPartnersHe,
};

export const referralsSectionDe: Translation<typeof referralsSectionEn> = {
  referrals: referralsDe,
  partnerPortal: partnerPortalDe,
  adminPartners: adminPartnersDe,
};
