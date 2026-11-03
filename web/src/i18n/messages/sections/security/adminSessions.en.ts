/**
 * `adminSessions.*` texts: the platform admin's card of a client team's
 * sign-ins on /admin/clients/[businessId], and ending one member's
 * sessions, in English: the reference that it is typed against.
 */

export const adminSessionsEn = {
  title: "Team sign-ins",
  description:
    "Who in this client's team is signed in, and on how many devices. When a phone is lost or an account may be taken over, end every session of that person: they sign in again.",
  roles: {
    owner: "Owner",
    staff: "Staff",
    agency: "Agency",
  },
  unnamed: "Member without a name",
  devices: {
    one: "Signed in on {count} device",
    other: "Signed in on {count} devices",
  },
  notSignedIn: "Not signed in",
  /** The card folded into a row on a phone. */
  signedIn: {
    one: "{count} signed in",
    other: "{count} signed in",
  },
  lastUsed: "Last used {date}",
  end: "End sessions",
  endLabel: "End sessions of {name}",
  endTitle: "End every session of {name}?",
  endDescription:
    "Every browser and phone of {name} will have to sign in again. The platform's audit log records that you did it.",
  ended: {
    one: "{count} session ended",
    other: "{count} sessions ended",
  },
} as const;
