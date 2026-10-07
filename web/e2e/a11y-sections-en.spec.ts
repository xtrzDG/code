/**
 * Every section of a business passes the accessibility audit in both
 * themes, in English (support/axe.ts; Hebrew in a11y-sections-he.spec.ts).
 */

import { auditEverySection } from "./support/axe";

auditEverySection("en");
