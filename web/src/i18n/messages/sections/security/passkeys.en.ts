/**
 * `passkeys.*` texts: passkeys (WebAuthn) in Account → Security, as the
 * second step of a sign-in and to confirm it is you, in English: the
 * reference that the other languages are typed against.
 */

export const passkeysEn = {
  title: "Passkeys",
  description:
    "Confirm it is you with your fingerprint, face or device PIN instead of a code. A passkey works only on this site, so it cannot be phished.",
  recommended: "The safest second factor: add a passkey on each device you use.",
  unavailable:
    "Passkeys are not set up on this server yet. Use the authenticator app below.",
  unsupported:
    "This browser cannot use passkeys. Open the cabinet in another browser or use the authenticator app.",
  empty: "No passkeys yet.",
  add: "Add a passkey",
  adding: "Waiting for your device…",
  added: "Passkey added",
  addedOn: "Added {date}",
  lastUsed: "Last used {date}",
  neverUsed: "Not used yet",
  synced: "Synced across your devices",
  suspended:
    "Refused: a copy of this passkey may be in use. Remove it and add it again.",
  name: "Name",
  rename: "Rename",
  renameLabel: "Rename {name}",
  renameTitle: "Rename the passkey",
  renameHint: "For example, the device or password manager that keeps it.",
  renamed: "Passkey renamed",
  save: "Save",
  remove: "Remove",
  removeLabel: "Remove {name}",
  removeTitle: "Remove this passkey?",
  removeDescription:
    "You will no longer be able to sign in with it. Remove it from the device too.",
  removed: "Passkey removed",
  signIn: {
    use: "Use a passkey",
    waiting: "Waiting for your passkey…",
    description: "Confirm with the passkey on this device or your phone.",
    useCode: "Use a code instead",
    usePasskey: "Use a passkey instead",
  },
  enrollment: {
    description:
      "Admins sign in with a second factor. A passkey is the safest: add one now, or set up an authenticator app.",
    add: "Add a passkey",
    useApp: "Set up an authenticator app instead",
  },
  stepUp: {
    use: "Confirm with a passkey",
    description:
      "Confirm with the passkey on this device or your phone. Nothing is sent.",
    useLoginCode: "Send me a login code instead",
    orCode: "or enter a code",
  },
  errors: {
    cancelled: "The passkey request was cancelled or timed out. Try again.",
    alreadyAdded: "This device already keeps a passkey for your account.",
    wrongSite:
      "Passkeys work only at the cabinet's usual address. Open it there and try again.",
    unsupported:
      "This browser cannot use passkeys. Try another browser or use a code.",
    rejected: "The passkey could not be confirmed. Try again.",
    suspended:
      "This passkey was refused: a copy of it may be in use. Use another way to sign in, then remove it.",
    unavailable: "Passkeys are not available here. Use a code instead.",
  },
} as const;
