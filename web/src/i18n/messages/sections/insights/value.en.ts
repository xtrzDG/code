/**
 * `value.*` texts: what the assistant is worth (the owner's hero on the
 * dashboard, the average check, the change chips) and a staff member's
 * queue of the day, in English: the reference that ru and ka are typed
 * against.
 */

export const valueEn = {
  hero: {
    title: "What your assistant did",
    reports: "Reports",
    bookingsLabel: "Bookings made by the assistant",
    requestsLabel: "Requests taken by the assistant",
    bookingsHint: "made in conversations and still on",
    requestsHint: "orders and requests it took down",
    noMoney: "Set your average check to see what this is worth.",
    afterHours: { one: "{count} after hours", other: "{count} after hours" },
    afterHoursHint: "conversations while you were closed",
    hoursSaved: { one: "~{count} staff hour saved", other: "~{count} staff hours saved" },
    minutesSaved: { one: "~{count} staff minute saved", other: "~{count} staff minutes saved" },
    savedHint: "{replies} replies written and {calls} calls answered for you",
    conversations: { one: "{count} conversation", other: "{count} conversations" },
    conversationsHint: "customers who wrote or called",
  },
  check: {
    owner: "Average check {money}",
    typical: "Average check {money}, typical for your kind of business",
    none: "No average check yet, so no money estimate",
    set: "Set the average check",
    change: "Change",
    inputLabel: "Average check, {currency}",
    useTypical: "Use the typical {money}",
    saved: "The average check is saved",
    cleared: "The typical check is used again",
    positive: "Enter an amount above zero.",
    hint: "What one booking brings on average. It turns bookings into money; real prices of your services will replace it later.",
  },
  delta: {
    up: "Up {change} vs {against}",
    down: "Down {change} vs {against}",
    same: "No change vs {against}",
    againstDay: "the day before",
    againstDays: { one: "the previous {count} day", other: "the previous {count} days" },
  },
  queue: {
    title: "Your queue today",
    mine: "Assigned to you",
    mineHint: "Conversations you look after",
    requests: "New requests",
    requestsHint: "Requests nobody has handled yet",
    bookings: "Bookings today",
    bookingsHint: "{upcoming} still to come · {unconfirmed} to confirm",
    bookingsLoading: "Today's bookings",
  },
} as const;
