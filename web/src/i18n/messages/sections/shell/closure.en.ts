/**
 * `closure.*` texts: closing a business and deleting it for good (the
 * countdown banner over its cabinet, the danger zone of Settings →
 * Business), deleting one's own account and the certificates of deleted
 * businesses (Account → Security), in English: the reference that the
 * other languages are typed against.
 */

export const closureEn = {
  banner: {
    label: "Business closing",
    title: "This business is closing",
    countdown: {
      one: "Everything in it will be deleted for good in {count} day, on {date}",
      other: "Everything in it will be deleted for good in {count} days, on {date}",
    },
    due: "The 30 days are over: the deletion starts within the hour.",
    deleting: "The business is being deleted. This can no longer be stopped.",
    unpaid: "It was closed because the subscription ended unpaid.",
    keep: "Keep the business",
    pay: "Pay to keep it",
    open: "Closing details",
    kept: "The business is open again",
  },
  zone: {
    title: "Close this business",
    description:
      "For when the business stops using the assistant. An owner can change their mind for 30 days; after that the business is deleted for good.",
    willPause: "The assistant stops answering customers, and every channel is disconnected.",
    willStopCharges: "Automatic charges stop: nothing more is billed.",
    willDelete:
      "After 30 days, everything in the business is deleted for good: conversations, customers, bookings, recordings, files and knowledge.",
    willKeep: "Issued invoices and the audit log are kept for as long as the law requires.",
    exportFirst: "Download a full copy of the data first",
    action: "Close business…",
    dialogTitle: "Close the business?",
    dialogDescription:
      "The assistant stops answering and the channels are disconnected now. The business is deleted for good in 30 days unless an owner keeps it.",
    confirm: "Close the business",
    closing: "Closing…",
    closed: "The business is closing",
    pendingTitle: "The business is closing",
    closedBy: "{name} closed it on {date}",
    closedOn: "Closed on {date}",
    unpaidHint: "It was closed because the subscription ended unpaid: pay in Billing, then keep the business here.",
    keepHint: "Keeping it brings the channels back; switch the assistant on again when you are ready.",
    keep: "Keep the business",
    billing: "Open Billing",
    export: "Download the data",
    deletingTitle: "The business is being deleted",
    deletingDescription:
      "The deletion has begun and can no longer be stopped. The owners get the deletion certificate in Account → Security.",
  },
  account: {
    title: "Delete your account",
    description:
      "Signs you out everywhere and deletes your sign-in methods (passkeys, authenticator app, recovery codes), your notification settings and app notifications. You leave every business you are a member of; their own data stays with them.",
    ownerNote: "The last owner of a business closes it first (Settings → Business) or makes another member an owner.",
    platformNote: "Members of the platform team leave the team (Admin → Team) before deleting their account.",
    action: "Delete account…",
    dialogTitle: "Delete your account?",
    dialogDescription: "This cannot be undone. You can sign up again later with the same email or phone, as a new account.",
    confirm: "Delete account",
    deleting: "Deleting…",
    lastOwner: "You are the last owner of {names}. Close the business in its Settings → Business, or make another member an owner, first.",
    lastBrandOwner: "You are the only owner of the brand {names}. Make another person a brand owner first.",
    lastOwnerUnnamed: "You are the last owner of a business or brand. Close it, or make another person an owner, first.",
    platformTeam: "Members of the platform team leave the team (Admin → Team) before deleting their account.",
  },
  deletions: {
    title: "Deleted businesses",
    description: "Businesses you owned that were closed and deleted. Each certificate says what was deleted, when, and what the law keeps.",
    reasonOwner: "Closed by an owner",
    reasonUnpaid: "Closed after the subscription ended unpaid",
    inProgress: "Being deleted",
    completedOn: "Deleted on {date}",
    startedOn: "Deletion began on {date}",
    certificate: "Certificate (PDF)",
    downloading: "Downloading…",
  },
} as const;
