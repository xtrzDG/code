/**
 * `updates.*` texts: one story for updates in the owner's words, in
 * English. What customers get now and what is still pending (the owner's
 * checks and drafts among it), which of the owner's checks failed and how
 * to fix it, "Check now", the test chat's two choices and the gate before
 * publishing without checks. Version numbers live only under Advanced →
 * History.
 */

export const updatesEn = {
  expectation: {
    must_mention: "the answer must mention “{text}”",
    must_not_mention: "the answer must not mention “{text}”",
    must_hand_off: "the answer must pass the customer to a person",
    must_create_lead: "the answer must take a request",
  },
  failed: {
    one: "Your check did not pass: “{question}” — {expectation}",
    many: {
      one: "{count} of your checks did not pass",
      other: "{count} of your checks did not pass",
    },
    rest: "Everything else passed. Customers keep the previous answers until the check passes.",
    result: "Your check did not pass",
    openCheck: "Open the check",
    fixAnswer: "Fix the answer",
    answered: "The assistant answered",
    applyAfterFix: "Apply changes",
  },
  pending: {
    checksTitle: "Your checks",
    checksHint: "The update asks these first. If one does not pass, customers keep the previous answers.",
    added: "New check: “{question}”",
    changed: "Changed check: “{question}”",
    draftsTitle: "Drafts",
    draftsHint: "Built by hand and never given to customers. Discarding one keeps your changes.",
    draft: "Draft of {date}",
    open: "Open",
    discard: "Discard",
    discardLabel: "Discard the draft of {date}",
    discardTitle: "Discard this draft?",
    discardDescription: "Customers never got it. Your changes stay: the next “Apply changes” builds from them.",
    discarded: "Draft discarded",
    onlyDrafts: "Everything you changed reaches customers. A draft is left over:",
  },
  checkNow: {
    action: "Check now",
    actionLabel: "Check “{question}” now",
    checking: "Checking…",
    hint: "One test conversation with what customers get now.",
    passed: "Passed with what customers get now.",
    failed: "Did not pass with what customers get now.",
    errored: "The check could not finish. Try again in a minute.",
    notLive: "Nothing reaches customers yet: the check runs with the first “Apply changes”.",
    limited: "You checked a lot this hour. Try again later.",
    checkedAt: "Checked {date}",
  },
  language: {
    auto: "The question's language",
  },
  chat: {
    target: "Talk to",
    live: "What customers get now",
    changes: "With your changes",
    history: "From History: update {number}",
    noteLive: "You talk to what customers get now. Test conversations do not reach customers, staff or billing.",
    noteChanges: "You talk to the assistant with your latest changes, before customers get them. Test conversations do not reach customers, staff or billing.",
    noteHistory: "You talk to an update from History. Test conversations do not reach customers, staff or billing.",
  },
  publishGate: {
    adminOnly: "Platform admins only",
  },
} as const;
