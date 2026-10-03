/**
 * `notifications.*` texts of Settings → Notifications (this device, my
 * events and quiet hours, staff contacts' delivery and checks) and of the
 * notification link page, in English: the reference that ru and ka are
 * typed against.
 */

export const notificationsEn = {
  device: {
    title: "On this device",
    description: "Handoffs, requests and bookings arrive as notifications on this phone or computer, even when the cabinet is closed.",
    on: "On",
    off: "Off",
    enable: "Enable notifications on this device",
    disable: "Turn off on this device",
    test: "Send a test",
    enabled: "Notifications are on for this device",
    disabled: "Notifications are off for this device",
    unsupported: "This browser cannot show notifications. On an iPhone or iPad, add the cabinet to the Home Screen (Share → Add to Home Screen) and open it from there.",
    denied: "Notifications are blocked for this site. Allow them in the browser's site settings and try again.",
    notConfigured: "Notifications on devices are not set up on this server yet.",
    dismissed: "Notifications were not allowed. Press the button again when you are ready.",
    failed: "Notifications could not be turned on in this browser. Try again.",
    lastDelivered: "Last notification {time}",
    neverDelivered: "No notifications yet",
    lastError: "The last one did not arrive: {error}",
    otherDevices: "My other devices",
    otherDevice: "Device added {date}",
    removeOther: "Turn off",
    removeOtherLabel: "Turn off notifications on the device added {date}",
    removed: "Notifications are off on that device",
    testDelivered: "The test notification is on its way to this device",
    testFailed: "The test did not reach this device: {error}",
    testPending: "The test to this device will be tried again: {error}",
  },
  mine: {
    title: "What reaches me",
    description: "Your choice for your own devices in this business. Times are in the business time zone, {timeZone}.",
    save: "Save",
    saved: "Your notification choices are saved",
  },
  preferences: {
    events: "Notify about",
    noEvents: "Nothing is selected: no notifications arrive.",
    event: {
      handoff: "Customers who need a person",
      lead: "New requests",
      booking: "Bookings: new, moved and cancelled",
    },
    quietHours: "Quiet hours",
    quietHoursHint: "Notifications wait until the quiet hours end. Urgent handoffs still arrive.",
    quietHoursToggle: "Hold notifications during these hours",
    quietFrom: "From",
    quietUntil: "Until",
    errors: {
      format: "Enter a time such as 22:00",
      same: "The start and the end must differ",
    },
    summary: {
      everything: "Everything, at any time",
      events: "Only: {events}",
      nothing: "Nothing",
      quiet: "quiet {from}–{until}",
    },
    short: {
      handoff: "handoffs",
      lead: "requests",
      booking: "bookings",
    },
  },
  contacts: {
    test: "Send a test",
    testLabel: "Send a test notification to {name}",
    testDelivered: "The test reached {name}",
    testSimulated: "No provider here: the test to {name} was written to the server log",
    testFailed: "The test to {name} did not arrive: {error}",
    testPending: "The test to {name} will be tried again: {error}",
    providerMissing: "Not set up on the server",
    providerMissingHint: "Nothing is sent this way until the platform's {channel} provider is configured.",
    status: {
      delivered: "Delivered",
      pending: "Waiting",
      dead: "Not delivered",
    },
    deliveredAt: "Delivered {time}",
    attemptedAt: "Tried {time}",
    never: "Nothing sent yet",
    telegramLinked: "Linked as @{username}",
  },
  link: {
    expiredTitle: "This link has expired",
    expiredDescription: "Notification links work for 7 days. Open the business to find what the notification was about.",
    invalidTitle: "This link does not work",
    invalidDescription: "It may be cut short, or meant for another account. Sign in with the account the notification was sent to.",
    openBusiness: "Open the business",
    toBusinesses: "My businesses",
  },
} as const;
