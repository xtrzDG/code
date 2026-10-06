/**
 * `dataTasks.*` texts: the post-deploy data tasks card of the admin system
 * page and the lists' "still indexing" note, in English: the reference that
 * ru and ka are typed against.
 */

export const dataTasksEn = {
  title: "Data tasks after a deploy",
  description:
    "Document migrations and lookup column backfills the batch worker runs by itself in batches of {size} rows. The next release is promoted only once every task is done.",
  open: {
    one: "{count} task open",
    other: "{count} tasks open",
  },
  allDone: "Every task is done",
  failed: "{count} failed",
  stalled: "{count} stalled for over a day",
  settled: "No worker of another release is running: tasks run now.",
  waiting: "Waiting for workers of {releases} to stop (about {time}).",
  waitingUnnamed: "Waiting for workers of an unnamed release to stop (about {time}).",
  none: "This release has no data tasks.",
  openCaption: "Open data tasks",
  doneCaption: "Done data tasks",
  showDone: {
    one: "Show {count} done task",
    other: "Show {count} done tasks",
  },
  hideDone: "Hide done tasks",
  columns: {
    task: "Task",
    status: "Status",
    progress: "Progress",
    when: "When",
    actions: "Actions",
  },
  kinds: {
    migrate_documents: "Rewrite documents to version {version}",
    backfill_lookup: "Fill the lookup column",
  },
  statuses: {
    pending: "Waiting",
    running: "Running",
    done: "Done",
    failed: "Failed",
  },
  lists: {
    customers: "Customers list",
    knowledge: "Knowledge list",
  },
  holdsBack: "Holds back: {lists}",
  rows: "{scanned} of about {estimate} rows",
  rowsUnknown: "{scanned} rows looked at",
  changed: "{count} changed, {batches} batches",
  failedRows: "{count} rows could not be upgraded: {keys}",
  dueSince: "Due since {time}",
  doneAt: "Done {time}",
  lastBatch: "Last batch {time}",
  isStalled: "Stalled",
  retry: "Walk again",
  retried: "The task walks its table again.",
  indexing: {
    title: "Still indexing",
    body: "A data update after the last release is still running, so some older entries may be missing from this list for a few minutes.",
  },
} as const;
