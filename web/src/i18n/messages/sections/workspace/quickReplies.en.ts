/**
 * `quickReplies.*` texts of Settings → Quick replies (replies the team
 * sends often, one text per language), in English: the reference that ru
 * and ka are typed against.
 */

export const quickRepliesEn = {
  description:
    "Replies your team sends often, ready in every language of your business. In a conversation, type / to insert one: the customer's name and booking fill in by themselves.",
  add: "New quick reply",
  loading: "Loading quick replies…",
  emptyTitle: "No quick replies yet",
  emptyDescription: "Opening hours, directions, “we'll call you back”: write them once, send them in two taps.",
  listLabel: "Quick replies",
  languages: "Languages",
  variablesUsed: "Fills in",
  edit: "Edit",
  editLabel: "Edit the quick reply “{title}”",
  delete: "Delete",
  deleteLabel: "Delete the quick reply “{title}”",
  confirmDelete: {
    title: "Delete this quick reply?",
    description: "“{title}” disappears from the picker for the whole team.",
    confirm: "Delete",
  },
  deleted: "Quick reply deleted",
  saved: "Quick reply saved",
  editor: {
    newTitle: "New quick reply",
    editTitle: "Edit quick reply",
    description: "Write it in each language your customers use. Staff see the text in the conversation's language.",
    title: "Name",
    titleHint: "What the team sees in the picker.",
    shortcut: "Shortcut",
    shortcutHint: "Typed after / in the reply box: letters, digits, - and _.",
    shortcutInvalid: "Use letters, digits, - and _ only, without spaces.",
    texts: "Text",
    textIn: "Text in {language}",
    textHint: "Leave a language empty if you do not need it. At least one text is required.",
    needOneText: "Write the text in at least one language.",
    insert: "Insert",
    insertLabel: "Insert {variable} into the text in {language}",
    preview: "Preview",
    previewHint: "With an example customer and booking.",
    sample: {
      name: "Nino",
      bookingTime: "Sat, 19:30",
    },
    save: "Save",
    saving: "Saving…",
    cancel: "Cancel",
    length: "{count} / {max}",
  },
  variables: {
    name: "Customer's name",
    booking_time: "Booking time",
    business_name: "Business name",
  },
  errors: {
    shortcut_taken: "Another quick reply already uses this shortcut.",
    too_many_quick_replies: "A business keeps at most 100 quick replies. Delete one you no longer use.",
    unknown_variable: "Only {name}, {booking_time} and {business_name} can be filled in. Check the braces in the text.",
    duplicate_language: "Each language can have one text.",
  },
} as const;
