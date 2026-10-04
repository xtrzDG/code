/**
 * `devices.*` texts: Account → Security → "Where you are signed in" (the
 * person's sessions, ending one or all the others), in English: the
 * reference that ru and ka are typed against.
 */

export const devicesEn = {
  title: "Where you are signed in",
  description:
    "Every browser and phone signed in to your account. A session nobody uses for 7 days ends by itself.",
  descriptionAdmin:
    "Every browser and phone signed in to your account. As a platform admin, a session ends after 12 hours without use and a day after the sign-in.",
  thisDevice: "This device",
  kind: {
    desktop: "Computer",
    phone: "Phone",
    tablet: "Tablet",
    unknown: "Device",
  },
  unknownBrowser: "Unknown browser",
  on: "{browser} on {system}",
  signedIn: "Signed in {date}",
  lastUsed: "Last used {date}",
  from: "from {address}",
  twoFactor: "With the authenticator app",
  oneFactor: "With a login code",
  ends: "Ends by itself {date}",
  end: "Sign out",
  endLabel: "Sign out {device}",
  endTitle: "Sign out this device?",
  endDescription: "Whoever uses it will have to sign in again.",
  ended: "The device is signed out",
  endOthers: "Sign out everywhere else",
  endOthersTitle: "Sign out every other device?",
  endOthersDescription:
    "Every browser and phone except this one will have to sign in again.",
  endedOthers: {
    one: "{count} device signed out",
    other: "{count} devices signed out",
  },
  onlyThis: "Only this device is signed in.",
  notYou:
    "Do not recognise a device? Sign it out, then turn on the authenticator app above.",
} as const;
