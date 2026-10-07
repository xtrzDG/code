/**
 * `inboxTriage.*` texts of working through the inbox list: row density,
 * the list column's width, the keyboard, selecting several conversations
 * and resolving them at once, and a row's details on hover, in English:
 * the reference that ru and ka are typed against.
 */

export const inboxTriageEn = {
  density: {
    label: "Rows",
    comfortable: "Comfortable",
    compact: "Compact",
  },
  resize: {
    label: "Width of the conversation list",
    hint: "Drag, or use the arrow keys. Double-click goes back to the usual width.",
  },
  keys: {
    open: "Keyboard shortcuts",
    title: "Keyboard shortcuts",
    description: "Work through the list without the mouse. The keys work whenever you are not typing.",
    listHint: "J and K move through the list, E marks resolved, A takes the conversation, X selects it, question mark shows every key.",
    resolveNote: "Resolved: a handoff goes back to the assistant, and an open request is marked won. Undo is in the message that follows.",
    actions: {
      next: "Next conversation",
      previous: "Previous conversation",
      open: "Open the conversation",
      resolve: "Mark resolved",
      assign: "Take it: you handle it",
      select: "Select it for a bulk action",
      search: "Search",
      help: "Show these keys",
      clear: "Clear the selection",
    },
  },
  select: {
    row: "Select the conversation with {name}",
    all: "Select every conversation with something to resolve",
    count: {
      one: "{count} selected",
      other: "{count} selected",
    },
    resolve: "Mark resolved",
    clear: "Clear selection",
  },
  resolved: {
    one: "{count} conversation resolved",
    other: "{count} conversations resolved",
  },
  resolvedPartly: "{done} of {total} resolved. Someone changed the others a moment earlier; the list shows how they stand now.",
  undone: "Back as it was",
  undonePartly: "Some could not go back: someone changed them meanwhile. The list shows how they stand now.",
  nothingToResolve: "Nothing waits in this conversation: no open handoff or request.",
  alreadyYours: "You already handle this conversation.",
  age: {
    now: "now",
    minutes: "{count} min",
    hours: "{count} h",
    days: "{count} d",
  },
  details: {
    source: "Came from",
    assignee: "Handled by",
    lastMessage: "Last message",
  },
} as const;
