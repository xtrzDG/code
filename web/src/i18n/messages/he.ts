import type { PartialMessages } from "../translate";
import { shellHe } from "./sections/shell";
import { growthSectionHe } from "./sections/growth";
import { helpHe } from "./sections/help";
import { referralsSectionHe } from "./sections/referrals";
import { customersSectionHe } from "./sections/customers";
import { securityFlowHe } from "./sections/security";
import { setupFlowHe } from "./sections/setup";
import { siteHe } from "./sections/site";
import { assistantFlowHe } from "./sections/assistant";
import { contentHe } from "./sections/content";
import { insightsHe } from "./sections/insights";
import { workspaceHe } from "./sections/workspace";

/**
 * Hebrew texts (עברית), drafted by the team and awaiting a native
 * speaker's review (config.ts, NEEDS_REVIEW_LOCALES). Keys as in en.ts.
 */
export const he: PartialMessages = {
  ...shellHe,
  ...growthSectionHe,
  ...helpHe,
  ...referralsSectionHe,
  ...customersSectionHe,
  ...securityFlowHe,
  ...setupFlowHe,
  ...siteHe,
  ...assistantFlowHe,
  ...contentHe,
  ...insightsHe,
  ...workspaceHe,
};
