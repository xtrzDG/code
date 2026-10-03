/**
 * `inbox.*` texts of the team inbox list: its views, filters, rows and the
 * assign menu, in English: the reference that ru and ka are typed against.
 * Wording follows docs/glossary.md.
 */

export const inboxEn = {
  title: "Inbox",
  viewsLabel: "Show conversations",
  views: {
    needs_person: "Needs a person",
    requests: "Requests",
    mine: "Mine",
    unassigned: "Unassigned",
    all: "All",
  },
  viewCount: {
    one: "{count} conversation",
    other: "{count} conversations",
  },
  empty: {
    needs_person: {
      title: "Nobody is waiting for a person",
      description: "When the assistant passes a conversation to your team, it appears here at once.",
    },
    requests: {
      title: "No open requests",
      description: "Banquets, group visits and other requests the assistant takes wait here until someone handles them.",
    },
    mine: {
      title: "Nothing is assigned to you",
      description: "Conversations you take, or that are given to you, wait here while they need the team.",
    },
    unassigned: {
      title: "Everything has someone",
      description: "Conversations that need the team and have nobody to handle them appear here.",
    },
    all: {
      title: "No conversations yet",
      description: "Conversations appear here as soon as customers write or call the assistant.",
    },
  },
  showAll: "See all conversations",
  loading: "Loading the inbox…",
  listLabel: "Conversations",
  searchLabel: "Search all conversations",
  searchPlaceholder: "Search: name, phone or text",
  filters: {
    open: "Filters",
    openWithCount: "Filters ({count})",
    title: "Filters",
    description: "Period, status and test conversations apply to all conversations and to search.",
    show: "Show conversations",
    clear: "Clear filters",
    includeTest: "Include test conversations",
  },
  results: "Results for “{search}”",
  clearSearch: "Clear search",
  row: {
    unassigned: "Nobody assigned",
    assignedTo: "Handled by {name}",
    you: "You",
    notes: {
      one: "{count} note",
      other: "{count} notes",
    },
    request: "Request: {type}",
    waiting: "Waiting since {time}",
  },
  assign: {
    open: "Assign",
    menuLabel: "Who handles this conversation",
    handledBy: "Handled by {name}",
    handledByYou: "You handle it",
    automatically: "Assigned automatically",
    nobody: "Nobody handles it yet",
    takeIt: "Take it",
    unassign: "Unassign",
    you: "You",
    teammate: "Team member",
    waiting: {
      one: "{count} waiting",
      other: "{count} waiting",
    },
    loading: "Loading the team…",
    assigned: "{name} handles this conversation now",
    taken: "You handle this conversation now",
    cleared: "Nobody is assigned now",
    conflict: "Someone else changed who handles this conversation a moment ago. Here is how it stands now.",
    colleague: "A colleague handles this conversation. Ask an owner to hand it over.",
    notMember: "That person is no longer in the team.",
  },
} as const;
