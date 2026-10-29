/**
 * Every section of a business passes the accessibility audit in both
 * themes, in English (support/axe.ts; Italian in a11y-sections-it.spec.ts).
 */

import { auditEverySection } from "./support/axe";

auditEverySection("en");
