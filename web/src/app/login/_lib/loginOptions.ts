/**
 * What the sign-in page offers, from GET /v1/auth/login-options: only the
 * ways that can deliver a code right now.
 */

import type { OtpDeliveryChannel, Schema } from "@/api/types";
import type { LoginMethod, OtpStartBody } from "@/lib/countries";

export type LoginOptions = Schema<"LoginOptionsView">;

/** Why phone sign-in cannot start for the chosen country (null: it can). */
export type PhoneLoginBlock = "restricted" | "noChannels" | null;

export function phoneLoginBlock(
  options: LoginOptions | undefined,
): PhoneLoginBlock {
  if (!options) {
    return null;
  }
  if (options.is_sign_up_restricted) {
    return "restricted";
  }
  return options.is_phone_login_available ? null : "noChannels";
}

/** E-mail is offered unless the API says it cannot deliver codes now. */
export function isEmailLoginOffered(
  options: LoginOptions | undefined,
): boolean {
  return options?.is_email_login_available ?? true;
}

/** The method actually shown: e-mail falls back to phone when it is not offered. */
export function effectiveLoginMethod(
  method: LoginMethod,
  options: LoginOptions | undefined,
): LoginMethod {
  return method === "email" && !isEmailLoginOffered(options) ? "phone" : method;
}

/** No channel can deliver a code for any country: sign-in is down. */
export function isSignInUnavailable(
  options: LoginOptions | undefined,
): boolean {
  return options !== undefined && options.configured_channels.length === 0;
}

/** The phone channel to ask for: the chosen one if it still works, else the country's first. */
export function chooseDeliveryChannel(
  channels: readonly OtpDeliveryChannel[],
  chosen: OtpDeliveryChannel | null,
): OtpDeliveryChannel | null {
  if (chosen !== null && channels.includes(chosen)) {
    return chosen;
  }
  return channels[0] ?? null;
}

export type OtpStartBodyWithChannel = OtpStartBody & {
  preferred_delivery_channel?: OtpDeliveryChannel;
};

/** The start body with the chosen channel when the visitor had a choice. */
export function withDeliveryChannel(
  body: OtpStartBody,
  method: LoginMethod,
  channels: readonly OtpDeliveryChannel[],
  channel: OtpDeliveryChannel | null,
): OtpStartBodyWithChannel {
  if (method !== "phone" || channel === null || channels.length < 2) {
    return body;
  }
  return { ...body, preferred_delivery_channel: channel };
}

/** The phone channels to offer on the code screen besides the one used ("no code? send by SMS"). */
export function otherDeliveryChannels(
  channels: readonly OtpDeliveryChannel[],
  current: OtpDeliveryChannel,
): OtpDeliveryChannel[] {
  return channels.filter((channel) => channel !== current);
}
