/**
 * `adminStatus.*` texts: the platform admin's announcements for the public
 * status page and the cabinet's banner (Admin → System), in English: the
 * reference that ru and ka are typed against.
 */

export const adminStatusEn = {
  title: "Status page announcements",
  description: "What the public status page and the banner over every cabinet say. Each change is in the audit log.",
  create: "New announcement",
  openPage: "Open the status page",
  none: "No announcements yet",
  noneDescription: "Write one when a part of the platform is down, slow or about to be maintained.",
  status: {
    active: "Active",
    resolved: "Resolved",
  },
  edit: "Update",
  resolve: "Resolve",
  resolveTitle: "Resolve this announcement?",
  resolveBody: "The banner leaves every cabinet, and the status page lists it under past incidents.",
  published: "Announcement published",
  saved: "Announcement updated",
  resolvedToast: "Announcement resolved",
  form: {
    createTitle: "New announcement",
    editTitle: "Update the announcement",
    description: "Owners see it at once on the status page and over their cabinet.",
    level: "Level",
    levelHints: {
      info: "A notice: no part of the platform is marked as affected.",
      maintenance: "Planned work: give a start time to announce it in advance.",
      degraded: "Works, but slower or with some failures.",
      outage: "Does not work. Owners cannot hide this banner.",
    },
    components: "Affected parts",
    componentsHint: "While it is active, each chosen part shows this level on the status page.",
    textLabel: "Text in {language}",
    textHint: "English is required. Owners whose language is left empty read the English text.",
    startsAt: "Starts",
    startsAtHint: "Empty: now. A later time announces planned work.",
    expectedEnd: "Expected end",
    timeZone: "Times are in this device's time zone.",
    publish: "Publish",
    save: "Save",
    saving: "Saving…",
    errors: {
      textRequired: "Write the English text: at least 3 characters.",
      componentsRequired: "Choose at least one affected part.",
      time: "Enter a date and a time.",
      endBeforeStart: "The end must be after the start and in the future.",
      startTooLate: "The start can be at most 60 days ahead.",
    },
  },
} as const;
