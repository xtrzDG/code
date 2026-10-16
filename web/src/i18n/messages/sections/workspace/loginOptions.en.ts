/**
 * `loginOptions.*` texts of the sign-in code channels, in English: the
 * reference that ru and ka are typed against.
 */

export const loginOptionsEn = {
  channelLabel: "Send the code by",
  noPhoneChannels: "Login codes cannot be sent to phone numbers of this country right now.",
  useEmail: "Sign in with e-mail",
  nothingAvailable: "Sign-in is temporarily unavailable: there is no way to deliver login codes yet. Please try again later.",
  restricted: "Sign-up is not available in this country yet.",
} as const;
