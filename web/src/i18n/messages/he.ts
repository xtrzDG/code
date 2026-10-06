import type { PartialMessages } from "../translate";
import { shellHe } from "./sections/shell";
import { growthSectionHe } from "./sections/growth";
import { helpHe } from "./sections/help";
import { referralsSectionHe } from "./sections/referrals";

/**
 * Hebrew texts (עברית), drafted by the team and awaiting a native
 * speaker's review (config.ts, NEEDS_REVIEW_LOCALES). Keys as in en.ts.
 */
export const he: PartialMessages = {
  ...shellHe,
  ...growthSectionHe,
  ...helpHe,
  ...referralsSectionHe,
};
