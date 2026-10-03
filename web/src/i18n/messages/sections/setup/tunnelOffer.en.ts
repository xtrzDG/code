/**
 * `tunnelOffer.*`: the screens about what the business sells (a short
 * table that saves itself, or an import from the website or a menu) and
 * when it is open and takes bookings. English is the reference.
 */

export const tunnelOfferEn = {
  offer: {
    title: "What do you offer?",
    text: "Add what you sell with prices. The assistant only quotes what is here.",
    sourcesLabel: "How to add them",
    sources: {
      type: "Type them in",
      website: "From your website",
      menu: "From a menu photo or file",
    },
    tableLabel: "Your offer",
    name: "Name",
    namePlaceholder: "What customers can order or book",
    price: "Price, {currency}",
    pricePlaceholder: "0",
    duration: "Minutes",
    suggestion: "Example",
    suggestionsHint: "Examples are only saved once you give them a price. Remove the ones you don't offer.",
    addRow: "Add a line",
    removeRow: "Remove {name}",
    removeEmpty: "Remove this line",
    rowSaving: "Saving…",
    rowSaved: "Saved",
    rowFailed: "Not saved",
    priced: {
      one: "{count} item with a price",
      other: "{count} items with a price",
    },
    importedTitle: {
      one: "{count} item added from your import",
      other: "{count} items added from your import",
    },
    importBack: "Back to the list",
    importHint: "We read it and show you what we found. Nothing is saved before you check it.",
  },
  hours: {
    title: "When are you open?",
    text: "We've suggested the usual hours for your kind of business. Change anything that's different.",
    hoursLabel: "Opening hours",
    bookingsTitle: "How do bookings work?",
    slot: "A visit takes",
    partySize: "Most people in one booking",
    notice: "Book at least",
    noticeNone: "No notice needed",
    cancellation: "Cancellation rule",
    cancellationHint: "Customers hear it when they book or cancel.",
    resourceTitle: "What customers book",
    resourceHint: "You can add more later in Assistant → Knowledge.",
    resourceName: "Name",
    resourceCount: "How many",
    resourceCapacity: "People in each",
    resourcesReady: "Ready to book: {list}",
    minutes: {
      one: "{count} minute",
      other: "{count} minutes",
    },
    hoursCount: {
      one: "{count} hour",
      other: "{count} hours",
    },
    noticeHours: {
      one: "{count} hour ahead",
      other: "{count} hours ahead",
    },
    noticeDays: {
      one: "{count} day ahead",
      other: "{count} days ahead",
    },
    noticeMinutes: {
      one: "{count} minute ahead",
      other: "{count} minutes ahead",
    },
    errors: {
      noHours: "Open at least one day.",
      partySize: "Write a whole number from 1.",
      resourceName: "Name what customers book.",
      capacity: "Write a whole number from 1.",
      unitCount: "Write a whole number from 1.",
    },
  },
} as const;
