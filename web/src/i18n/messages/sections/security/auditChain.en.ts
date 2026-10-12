/**
 * `auditChain.*` texts of the tamper check of an audit log: the strip on
 * Settings → Audit (the owner's own log) and the platform admin's Audit
 * page, in English: the reference the other languages are typed against.
 */

export const auditChainEn = {
  title: "Tamper check",
  status: {
    unchecked: "Not checked yet",
    intact: "Intact",
    broken: "Changed",
  },
  verdict: {
    unchecked: "Each entry is sealed with the one before it. The first daily check runs within a day.",
    intact: "Each entry is sealed with the one before it, and the daily check found every entry as it was written.",
    broken: "The daily check found entry {position} not as it was written: {problem}. The platform team has been alerted.",
  },
  problems: {
    hash_mismatch: "it was changed",
    link_broken: "an entry before it was changed, removed or added",
    position_gap: "an entry before it was removed",
    head_lost: "the newest entries were cut off or rewritten",
    checkpoint_mismatch: "entries removed after the retention period are back",
  },
  checkedAt: "Checked {when}",
  verifiedThrough: "Checked through entry {position}",
  purgedThrough: "Entries up to {position} were removed after the retention period",
} as const;
