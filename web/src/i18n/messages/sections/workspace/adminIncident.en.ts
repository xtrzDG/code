/**
 * `adminIncident.*` texts of "Record incident" on the platform admin's
 * System page, in English: the reference that ru and ka are typed against.
 * The notice fields follow section 12.1 of the DPA.
 */

export const adminIncidentEn = {
  title: "Record incident",
  description:
    "Each affected business gets an entry in its audit log. A personal data breach also sends the DPA 12.1 notice to every owner of those businesses.",
  kind: "Type of incident",
  severity: "Severity",
  severityHint: "SEV1: most customers get no answers, or data left the platform. SEV2: a channel or feature is down for many. SEV3: a few businesses, or a workaround exists.",
  severityBreach: "A personal data breach is always SEV1.",
  name: "Title",
  nameHint: "One line for the log, without customer names.",
  startedAt: "Started",
  detectedAt: "Detected",
  detectedHint: "When the platform became aware; empty for now. For a breach the 48-hour notice period runs from here.",
  timeZone: "Times are in your device's time zone.",
  businesses: "Affected businesses",
  businessesHint: "Business ids (business_…) or links to their pages in Clients, one per line.",
  scope: {
    legend: "Which businesses",
    listed: "The businesses listed below",
    all: "Every business of the platform",
    allHint:
      "Recorded at once; the worker then walks every business in batches: each gets its audit entry, and for a breach its owners get the notice. The log shows how far it got.",
  },
  announcement: {
    offer: "Also publish a status announcement",
    offerHint: "Shown on the public status page and in every cabinet's banner from now on; resolve it on this page once the incident is over.",
    title: "Status announcement",
  },
  breach: {
    title: "Notice to owners",
    description:
      "Owners get it by e-mail, or by SMS without an address, in their cabinet language. English is required; add Georgian and Russian so each owner reads it in their own language.",
    subjects: "People concerned (approx.)",
    records: "Records concerned (approx.)",
    language: "Notice language",
    languages: {
      en: "English",
      ka: "Georgian",
      ru: "Russian",
    },
    complete: "complete",
    partial: "incomplete",
    fields: {
      nature: "What happened",
      subject_categories: "Categories of people",
      record_categories: "Categories of records",
      likely_consequences: "Likely consequences",
      measures: "Measures taken or proposed",
    },
  },
  submit: "Record incident",
  submitBreach: "Record and notify owners",
  saving: "Recording…",
  errors: {
    required: "Fill this in.",
    title: "Write 3 to 160 characters.",
    future: "This time is in the future.",
    order: "Detected cannot be before started.",
    businessIds: "Not a business id: {tokens}",
    tooManyBusinesses: "At most 1,000 businesses.",
    count: "A whole number from 0 to 1,000,000,000.",
    noticeRequired: "The English notice is required.",
    noticeIncomplete: "Fill all five texts of this language, or none.",
  },
} as const;
