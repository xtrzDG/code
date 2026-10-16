/**
 * Every section of a business passes the accessibility audit in both
 * themes, in Hebrew, right to left (support/axe.ts; English in
 * a11y-sections-en.spec.ts).
 */

import { auditEverySection } from "./support/axe";

auditEverySection("he");
