/**
 * `phoneNumbers.*` texts of a phone number the platform rents for the
 * business: the phone channel card's "Get a number", its search dialog,
 * the rented number and a request to the team, in English: the reference
 * that the other languages are typed against.
 */

export const phoneNumbersEn = {
  panel: {
    noNumber: "No phone number for calls yet? Take one from us: it answers with your assistant at once.",
    getNumber: "Get a number",
    rentedTitle: "Your number from us",
    monthly: "{price} a month",
    answering: "Answers with your assistant",
    connecting: "Connecting to your assistant…",
    releasing: "Being given back",
    giveBackHint: "To give the number back, disconnect the phone channel. It stops being billed and returns to the carrier.",
    requestTitle: "Number requested",
    requestText: "A {type} number in {country}. Our team arranges it and writes to you; it can take a few working days.",
    requestTextCity: "A {type} number in {country}, near {city}. Our team arranges it and writes to you; it can take a few working days.",
    cancelRequest: "Cancel the request",
    requestCancelled: "Request cancelled",
    ownerOnly: "Only an owner can take a number.",
  },
  tunnel: {
    title: "Phone calls",
    text: "Take a number from us and the assistant answers calls on it, in your customers' language. You can also do it later on the Channels page.",
  },
  dialog: {
    title: "Get a phone number",
    description: "A number in the country you choose, billed monthly with your plan.",
    country: "Country",
    countriesNow: "Get it now",
    countriesTeam: "Arranged by our team",
    type: "Kind of number",
    city: "City or area",
    cityHint: "Optional: we look for numbers near it.",
    search: "Find numbers",
    searching: "Looking for numbers…",
    close: "Close",
  },
  types: {
    local: "local",
    mobile: "mobile",
    toll_free: "toll-free",
  },
  typeOptions: {
    local: "Local (a city line)",
    mobile: "Mobile",
    toll_free: "Toll-free",
  },
  offers: {
    title: "Numbers you can take now",
    price: "{price} a month for any of them",
    none: "No free numbers of this kind there right now. Try without a city, another kind, or ask our team.",
    take: "Take",
    takeLabel: "Take {number}",
  },
  confirm: {
    title: "Take {number}?",
    price: "It costs {price} a month, billed with your plan from today.",
    channel: "It becomes your phone channel and answers with your assistant.",
    giveBack: "You can give it back any time by disconnecting the phone channel.",
    take: "Take the number",
    back: "Back to the list",
    done: "{number} is yours",
  },
  request: {
    requires_documents: "In this country the regulator asks for your business's documents before a number is issued. Our team arranges it with you.",
    on_request: "Our team arranges numbers of this kind here by hand.",
    ask: "Ask our team",
    sent: "Request sent: our team will write to you",
  },
  refusals: {
    numberTaken: "Someone has just taken this number. Search again and pick another one.",
    priceChanged: "The price of this kind of number has changed. Search again to see the new price.",
  },
} as const;
