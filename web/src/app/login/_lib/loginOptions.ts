/**
 * What the sign-in page offers, from GET /v1/auth/login-options: only the
 * ways that can deliver a code right now.
 */

import type { OtpDeliveryChannel, Schema } from "@/api/types";
import type { LoginMethod, OtpStartBody } from "@/lib/countries";

export type LoginOptions = Schema<"LoginOptionsView">;

/** Why phone sign-in cannot start for the chosen country (null: it can). */
export type PhoneLoginBlock = "restricted" | "noChannels" | null;

/** Some phone channel (SMS, WhatsApp, Telegram) has a provider, for some country. */
function hasPhoneChannel(options: LoginOptions): boolean {
  return options.configured_channels.some((channel) => channel !== "email");
}

/**
 * Why phone sign-in cannot start: the chosen country's own answer
 * (`options`) decides. While it loads, or after it failed, the last answer
 * of any country (`lastOptions`) still blocks phone when no phone channel
 * is set up at all (then no country has one), so the notice does not go
 * and come back between two answers.
 */
export function phoneLoginBlock(
  options: LoginOptions | undefined,
  lastOptions: LoginOptions | undefined = options,
): PhoneLoginBlock {
  if (!options) {
    return lastOptions !== undefined && !hasPhoneChannel(lastOptions) ? "noChannels" : null;
  }
  if (options.is_sign_up_restricted) {
    return "restricted";
  }
  return options.is_phone_login_available ? null : "noChannels";
}

/** E-mail is offered unless the API says it cannot deliver codes now. */
export function isEmailLoginOffered(options: LoginOptions | undefined): boolean {
  return options?.is_email_login_available ?? true;
}

/**
 * The method the page opens on: phone, or e-mail when codes go by e-mail
 * only (no phone channel is set up for any country). Opening on phone
 * there would greet every visitor with "codes cannot be sent to phone
 * numbers" and a button to the form that works. The server applies it to
 * the page's first HTML (openingMethod.ts); the country does not matter,
 * since `configured_channels` are the same for all of them.
 */
export function openingLoginMethod(options: LoginOptions): LoginMethod {
  return isEmailLoginOffered(options) && !hasPhoneChannel(options) ? "email" : "phone";
}

/** No channel can deliver a code for any country: sign-in is down. */
export function isSignInUnavailable(options: LoginOptions | undefined): boolean {
  return options !== undefined && options.configured_channels.length === 0;
}

/**
 * A code can be asked for by the method shown: sign-in is up and the method
 * delivers. The form of a method that does not deliver stays where it is
 * (it explains and offers the other one), it only cannot send.
 * `lastOptions` is the last answer of any country: whether e-mail delivers,
 * whether any phone channel is set up and whether sign-in is down are the
 * same for every country, so they hold while the chosen country's own
 * answer (`options`) loads or after it failed.
 */
export function canSendLoginCode(
  method: LoginMethod,
  options: LoginOptions | undefined,
  lastOptions: LoginOptions | undefined = options,
): boolean {
  if (isSignInUnavailable(lastOptions)) {
    return false;
  }
  return method === "email" ? isEmailLoginOffered(lastOptions) : phoneLoginBlock(options, lastOptions) === null;
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

export type OtpStartBodyWithChannel = OtpStartBody & { preferred_delivery_channel?: OtpDeliveryChannel };

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
