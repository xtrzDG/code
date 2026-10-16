/**
 * `dpaNotice.*` texts: the banner over an owner's cabinet when a new
 * version of the data processing agreement replaces the one the business
 * accepted, in English: the reference that ru and ka are typed against.
 */

export const dpaNoticeEn = {
  label: "New data processing agreement",
  title: "The data processing agreement has a new version ({version})",
  due: "It replaces the version you accepted. Read and accept it by {date}: applying changes to the assistant needs the current version.",
  overdue:
    "It replaces the version you accepted and was due by {date}: applying changes to the assistant needs the current version, so read and accept it now.",
  action: "Read and accept",
} as const;
