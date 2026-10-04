/**
 * `supportAccess.*` texts: the banner over a business's cabinet while
 * platform support looks into it (who, why, until when; the owner ends it
 * or lets support change things for some hours) and the read-only notice
 * support sees there, in English: the reference that ru and ka are typed
 * against.
 */

export const supportAccessEn = {
  label: "Platform support access",
  owner: {
    title: "Platform support is looking at your cabinet",
    who: "{name}: “{reason}”",
    someone: "Platform support",
    until: "until {time}",
    readOnly: "Support can only look; nothing can be changed without you.",
    end: "End access",
    endTitle: "End platform support's access?",
    endDescription:
      "Support leaves your cabinet at once, and their permission to change things ends too.",
    ended: "Platform support no longer has access",
    allow: "Let support make changes",
    allowHint:
      "For example, when you asked them to set up the assistant for you. Ends by itself.",
    allowedUntil: "Support may make changes until {time}",
    hours: "For how long",
    hourOptions: {
      one: "{count} hour",
      other: "{count} hours",
    },
    dayOption: "A day",
    weekOption: "A week",
    allowed: "Support may make changes",
    stopped: "Support can only look again",
    staff: "Only an owner can end it or let support make changes.",
  },
  support: {
    title: "You are looking at {name} as platform support",
    readOnly: "Read only: changes are refused.",
    canWrite: "Changes allowed by the owner until {time}",
    until: "Access ends at {time}",
    leave: "Leave the cabinet",
    left: "You left the cabinet",
  },
} as const;
