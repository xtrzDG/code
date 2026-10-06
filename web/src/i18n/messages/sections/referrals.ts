/**
 * Texts of the referral program: an owner's invitation and "Powered by"
 * link, the partner portal (/partner) and the platform admin's partners
 * and payouts (/admin/partners).
 *
 * Top-level keys are namespaces. They are spread into en.ts, ru.ts and
 * ka.ts, so they must not clash with the namespaces of the other
 * dictionaries. `ru` and `ka` are type-checked against `en`.
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
