/**
 * Facts of the accessibility statement (/[locale]/accessibility) that are
 * not texts: the day it was prepared (AgID's model asks for it, and for a
 * review at least once a year: update it with every review) and where
 * AgID takes reports when the provider's answer is unsatisfactory.
 */

/** The day the statement was prepared or last reviewed (YYYY-MM-DD, UTC). */
export const ACCESSIBILITY_STATEMENT_DATE = "2026-11-03";

/** AgID's online form for reports on accessibility (the enforcement procedure). */
export const AGID_REPORT_URL = "https://form.agid.gov.it/";

/** The known limitations, in the order the statement lists them. */
export const ACCESSIBILITY_LIMITATIONS = ["legalLanguage", "userContent", "thirdParty", "audit"] as const;
