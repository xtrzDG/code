/**
 * `adminAudit.*` texts of the platform admin's Audit page (/admin/audit):
 * the tamper check of every business's audit log and the platform's own
 * log (sign-ins, sign-outs, key rotations), in English: the reference the
 * other languages are typed against.
 */

export const adminAuditEn = {
  nav: "Audit",
  title: "Audit",
  description: "The daily tamper check of every audit log, and the platform's own log: failed sign-ins, lockouts, sign-outs and key rotations.",
  chains: {
    title: "Tamper check",
    platform: "Platform log",
    intact: "Unchanged logs",
    broken: "Changed logs",
    allIntact: "The latest checks found every business's log as it was written.",
    brokenList: "Logs found changed",
    business: "Business",
    entry: "Entry",
    problem: "Problem",
    checked: "Checked",
    platformName: "Platform",
  },
  log: {
    title: "Platform log",
    description: "Entries that name no business, newest first. A sign-in code's address shows only as a keyed digest, never the address.",
    filters: "Filter the platform log",
    event: "Event",
    allEvents: "All events",
    when: "When",
    what: "What",
    who: "Who",
    address: "Network address",
    entry: "Entry",
    empty: "No entries yet",
    emptyFiltered: "No entries for this event",
    unknownPerson: "Unknown person",
    system: "System",
    restricted: "The platform log shows every person's sign-ins with their network addresses, so only admins allowed to read the security log see it.",
  },
  events: {
    login_failed: "Wrong code",
    otp_locked: "Code locked",
    mfa_locked: "Second step locked",
    logout: "Signed out",
    key_rotation: "Key rotation",
  },
} as const;
