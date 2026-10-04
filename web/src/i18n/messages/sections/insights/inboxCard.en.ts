/**
 * `inboxCard.*` texts of a conversation in the team inbox: the folded
 * header, the quick actions, what waits in it, the details and notes
 * panels, quick replies and the technical details, in English: the
 * reference that ru and ka are typed against. Wording follows
 * docs/glossary.md.
 */

export const inboxCardEn = {
  back: "Back to the inbox",
  openDetails: "Details",
  openDetailsOf: "Details of the conversation with {name}",
  openNotes: "Notes",
  openNotesCount: {
    one: "Notes ({count})",
    other: "Notes ({count})",
  },
  panelLabel: "About this conversation",
  panelTabs: "Panel",
  actions: {
    label: "Quick actions",
    resolve: "Resolve",
    resolveHint: "The assistant answers this customer again",
    call: "Call",
    callLabel: "Call {phone}",
    book: "Book",
  },
  work: {
    needsPerson: "Needs a person",
    request: "Request",
    requestStatus: "Status of the request",
    since: "since {time}",
  },
  details: {
    title: "Details",
    customer: "Customer",
    channel: "Channel",
    language: "Language",
    started: "Started",
    lastMessage: "Last message",
    assignment: "Handled by",
  },
  technical: {
    title: "Technical details",
    hint: "What is behind the answers: the update of the assistant that gave them and its exact requests to your data.",
    model: "Model",
    models: "Models",
    tokens: "Tokens",
    cost: "AI cost",
    version: "Assistant version",
    toolCalls: {
      one: "{count} request to your data",
      other: "{count} requests to your data",
    },
    message: "Technical details of this message",
  },
  notes: {
    title: "Notes",
    hint: "Only your team sees this",
    description: "Notes stay inside your team: the customer and the assistant never see them.",
    label: "Note for the team",
    placeholder: "What was promised, who calls back, what to remember…",
    add: "Add note",
    adding: "Saving…",
    added: "Note saved. Only your team sees it.",
    by: "{name}, {time}",
    unknownAuthor: "Former team member",
    delete: "Delete note",
    confirmDelete: {
      title: "Delete this note?",
      description: "It disappears for the whole team.",
      confirm: "Delete",
    },
    deleted: "Note deleted",
    empty: "No notes yet. A note helps the next person: what was promised, who calls back.",
    loading: "Loading notes…",
    older: "Show older notes",
    length: "{count} / {max}",
  },
  quickReplies: {
    open: "Quick replies",
    hint: "Type / for quick replies",
    listLabel: "Quick replies",
    loading: "Loading quick replies…",
    empty: "No quick replies yet.",
    emptyOwner: "Create replies you send often in Settings → Quick replies.",
    manage: "Manage quick replies",
    noMatch: "No quick reply matches “/{query}”.",
    language: "In {language}",
    missing: "Fill in before sending:",
    fillLabel: "Value for {variable}",
    fill: "Fill in",
    placeholdersLeft: "Fill in the parts in braces before sending: {variables}.",
    variables: {
      name: "customer's name",
      booking_time: "booking time",
      business_name: "business name",
    },
  },
  composer: {
    placeholder: "Write to the customer…",
    sendLabel: "Send",
    unavailable: "You cannot write from here now",
  },
  request: {
    updated: "Request: {status}",
  },
  resolveConfirm: {
    title: "Mark as resolved?",
    description: "{name}: the assistant starts answering this customer again.",
    confirm: "Resolve",
  },
  resolved: "Marked as resolved. The assistant answers this customer again.",
  reopened: "The handoff is open again. The assistant stays silent until it is resolved.",
} as const;
