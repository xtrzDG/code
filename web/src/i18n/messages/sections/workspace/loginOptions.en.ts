/**
 * `loginOptions.*` texts of the sign-in code channels, in English: the
 * reference that it is typed against.
 */

export const loginOptionsEn = {
  channelLabel: "Send the code by",
  noEmail: "Login codes cannot be sent by e-mail right now.",
  noPhoneChannels: "Login codes cannot be sent to phone numbers of this country right now.",
  useEmail: "Sign in with e-mail",
  usePhone: "Sign in with a phone number",
  nothingAvailable: "Sign-in is temporarily unavailable. Please try again later.",
  restricted: "Sign-up is not available in this country.",
} as const;
