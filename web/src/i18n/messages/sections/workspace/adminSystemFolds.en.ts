/**
 * `adminSystem.folds.*` texts: what each card of the System page
 * (/admin/system) folded into a row on a phone says beside its name, in
 * English: the reference that it is typed against.
 */

export const adminSystemFoldsEn = {
  none: "None",
  live: { one: "{count} live", other: "{count} live" },
  stale: { one: "{count} stale", other: "{count} stale" },
  allClosed: "All closed",
  notClosed: { one: "{count} not closed", other: "{count} not closed" },
  due: { one: "{count} due", other: "{count} due" },
  deadJobs: { one: "{count} job", other: "{count} jobs" },
  noneInError: "None in error",
  inError: { one: "{count} in error", other: "{count} in error" },
  expiring: { one: "{count} token running out", other: "{count} tokens running out" },
  allMatch: "All match",
  noneOpen: "None open",
  open: { one: "{count} open", other: "{count} open" },
} as const;
