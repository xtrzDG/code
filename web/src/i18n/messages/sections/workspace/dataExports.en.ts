/**
 * `dataExports.*` texts: Settings → Privacy → "Export your data" (the full
 * export of the business and its tables as CSV) and the CSV buttons of
 * Bookings and the Inbox, in English: the reference that ru and ka are
 * typed against.
 */

export const dataExportsEn = {
  csv: {
    button: "Export CSV",
    bookingsHint: "The bookings the filters show, as a spreadsheet (CSV)",
    inboxLabel: "Export these conversations as CSV",
    inboxHint: "The chosen view and channel, every message included",
    tableLabel: "Download {table} as CSV",
    saved: "The file is downloaded",
    tables: {
      bookings: "Bookings",
      leads: "Leads",
      contacts: "Customers",
      conversations: "Conversations",
      audit_log: "Audit log",
    },
  },
  full: {
    title: "Export your data",
    description:
      "Everything kept for your business in one ZIP file: customers, conversations with every message, calls, bookings, leads, services, missed calls, feedback and the audit log, as JSON and as spreadsheets (CSV).",
    start: "Prepare full export",
    started: "The export is being prepared",
    working: "Preparing the archive. It takes a few minutes; you can leave this page and come back.",
    history: "Recent exports",
    empty: "No exports yet. Prepare one whenever you need a copy of your data.",
    requested: "Asked {date}",
    readyUntil: "Kept until {date}",
    download: "Download ZIP",
    downloadLabel: "Download the export asked {date}",
    downloadStarted: "The download has started",
    downloadsLeft: { one: "{count} of {total} downloads left", other: "{count} of {total} downloads left" },
    usedUp: "This export was downloaded three times. Prepare a new one for another copy.",
    gone: "This export is no longer kept. Prepare a new one.",
    sizeKb: "{size} KB",
    sizeMb: "{size} MB",
    records: { one: "{count} record", other: "{count} records" },
    failed: "The archive could not be made. Prepare it again; if it fails again, write to support.",
    status: {
      queued: "Waiting",
      running: "Preparing",
      ready: "Ready",
      expired: "Deleted",
      failed: "Failed",
    },
    linkNote:
      "Each download makes a one-time link that works for 10 minutes and only for you. An export can be downloaded three times within a day, and every owner is told who downloaded it, from which device and address.",
    erasedNote: "Customers whose data was erased are not in any export.",
  },
  tables: {
    title: "Tables as spreadsheets",
    description:
      "One table as CSV, for Excel, Numbers or Google Sheets. Bookings and the Inbox also export with the filters you choose there.",
  },
} as const;
