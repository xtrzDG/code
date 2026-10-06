import type { PartialMessages } from "../translate";
import { shellDe } from "./sections/shell";
import { growthSectionDe } from "./sections/growth";
import { helpDe } from "./sections/help";
import { referralsSectionDe } from "./sections/referrals";
import { customersSectionDe } from "./sections/customers";
import { securityFlowDe } from "./sections/security";
import { setupFlowDe } from "./sections/setup";
import { siteDe } from "./sections/site";
import { assistantFlowDe } from "./sections/assistant";

/**
 * German texts (Deutsch), drafted by the team and awaiting a native
 * speaker's review (config.ts, NEEDS_REVIEW_LOCALES). Keys as in en.ts.
 */
export const de: PartialMessages = {
  ...shellDe,
  ...growthSectionDe,
  ...helpDe,
  ...referralsSectionDe,
  ...customersSectionDe,
  ...securityFlowDe,
  ...setupFlowDe,
  ...siteDe,
  ...assistantFlowDe,
};
