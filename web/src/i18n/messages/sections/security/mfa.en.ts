/**
 * `mfa.*` texts: the second step of signing in (an authenticator code or a
 * recovery code), setting up an authenticator app, recovery codes shown
 * once, and the "confirm it is you" dialog of sensitive actions, in
 * English: the reference that ru and ka are typed against.
 */

export const mfaEn = {
  secondStep: {
    title: "Two-factor sign-in",
    description:
      "Open your authenticator app and enter the 6-digit code it shows for Assistant Workshop.",
    code: "Code from the app",
    recoveryDescription:
      "Enter one of the recovery codes you saved. Each code works once.",
    recoveryCode: "Recovery code",
    recoveryHint: "12 letters and digits, for example {example}",
    useRecovery: "Use a recovery code instead",
    useApp: "Use the authenticator app",
    verify: "Sign in",
    verifying: "Checking…",
    startOver: "Sign in again",
  },
  enrollment: {
    title: "Set up two-factor sign-in",
    description:
      "Platform admins sign in with a code from an authenticator app too. Set one up now: it takes a minute, and the next sign-ins only ask for the code.",
    start: "Set up now",
    starting: "Preparing…",
  },
  setup: {
    title: "Set up an authenticator app",
    stepInstall:
      "Install an authenticator app on your phone: Google Authenticator, Microsoft Authenticator, 1Password or another one.",
    stepScan: "Scan this QR code with the app, or type in the key.",
    stepCode: "Enter the 6-digit code the app shows.",
    qrLabel: "QR code for the authenticator app",
    key: "Key",
    copyKey: "Copy the key",
    code: "Code from the app",
    confirm: "Turn on",
    confirming: "Turning on…",
  },
  recovery: {
    title: "Save your recovery codes",
    description:
      "If you lose your phone, sign in with one of these codes instead of the app. Each code works once. They are shown only now: keep them in a password manager or print them.",
    copy: "Copy",
    download: "Download",
    fileHeading:
      "Assistant Workshop recovery codes for {account}. Each code works once.",
    saved: "I saved the codes somewhere safe",
    continue: "Continue",
  },
  stepUp: {
    title: "Confirm it is you",
    description: "This action needs a fresh confirmation.",
    totp: "Enter the code from your authenticator app.",
    loginCode: "We sent a code to {destination}. Enter it here.",
    sending: "Sending a code…",
    code: "Code",
    confirm: "Confirm",
    confirming: "Checking…",
    resend: "Send a new code",
    confirmed: "Confirmed. Doing it now.",
  },
  errors: {
    wrongCode: "The code is wrong or was already used. Try the newest code.",
    expired: "This sign-in has expired. Start again.",
    tooManyAttempts: "Too many wrong codes. Sign in again.",
    codeFormat: "Enter the 6 digits",
  },
} as const;
