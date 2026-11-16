import { describe, expect, it } from "vitest";

import {
  canSendLoginCode,
  chooseDeliveryChannel,
  isEmailLoginOffered,
  isSignInUnavailable,
  openingLoginMethod,
  otherDeliveryChannels,
  phoneLoginBlock,
  withDeliveryChannel,
  type LoginOptions,
} from "./loginOptions";

const options = (overrides: Partial<LoginOptions> = {}): LoginOptions => ({
  country_code: "GE",
  phone_channels: ["sms", "telegram"],
  configured_channels: ["sms", "telegram", "email"],
  is_phone_login_available: true,
  is_email_login_available: true,
  is_sign_up_restricted: false,
  ...overrides,
});

describe("login options", () => {
  it("offers everything until the options arrive", () => {
    expect(phoneLoginBlock(undefined)).toBeNull();
    expect(isEmailLoginOffered(undefined)).toBe(true);
    expect(isSignInUnavailable(undefined)).toBe(false);
    expect(canSendLoginCode("phone", undefined)).toBe(true);
    expect(canSendLoginCode("email", undefined)).toBe(true);
  });

  it("explains why phone sign-in cannot start", () => {
    expect(phoneLoginBlock(options())).toBeNull();
    expect(phoneLoginBlock(options({ is_sign_up_restricted: true, is_phone_login_available: false }))).toBe(
      "restricted",
    );
    expect(phoneLoginBlock(options({ phone_channels: [], is_phone_login_available: false }))).toBe("noChannels");
  });

  it("does not offer e-mail when it cannot deliver codes", () => {
    const noEmail = options({ is_email_login_available: false, configured_channels: ["sms", "telegram"] });

    expect(isEmailLoginOffered(noEmail)).toBe(false);
    expect(isEmailLoginOffered(options())).toBe(true);
  });

  it("sends a code only by a method that delivers", () => {
    const noEmail = options({ is_email_login_available: false, configured_channels: ["sms", "telegram"] });
    const noChannelHere = options({ phone_channels: [], is_phone_login_available: false });
    const restricted = options({ phone_channels: [], is_phone_login_available: false, is_sign_up_restricted: true });
    const nothing = options({
      phone_channels: [],
      configured_channels: [],
      is_phone_login_available: false,
      is_email_login_available: false,
    });

    expect(canSendLoginCode("phone", options())).toBe(true);
    expect(canSendLoginCode("email", options())).toBe(true);
    // The method shown does not deliver: its form stays and cannot send.
    expect(canSendLoginCode("email", noEmail)).toBe(false);
    expect(canSendLoginCode("phone", noEmail)).toBe(true);
    expect(canSendLoginCode("phone", noChannelHere)).toBe(false);
    expect(canSendLoginCode("email", noChannelHere)).toBe(true);
    expect(canSendLoginCode("phone", restricted)).toBe(false);
    // Sign-in is down: neither method sends.
    expect(canSendLoginCode("phone", nothing)).toBe(false);
    expect(canSendLoginCode("email", nothing)).toBe(false);
    // An answer that offers e-mail although no channel is set up is still "down".
    expect(canSendLoginCode("email", { ...nothing, is_email_login_available: true })).toBe(false);
  });

  it("keeps what is the same for every country while the chosen country's answer loads", () => {
    const noEmail = options({ is_email_login_available: false, configured_channels: ["sms", "telegram"] });
    const nothing = options({
      phone_channels: [],
      configured_channels: [],
      is_phone_login_available: false,
      is_email_login_available: false,
    });

    // E-mail and sign-in being down come from the last answer of any country.
    expect(canSendLoginCode("email", undefined, noEmail)).toBe(false);
    expect(canSendLoginCode("phone", undefined, nothing)).toBe(false);
    // The phone form waits for its own country: until then it may send.
    expect(canSendLoginCode("phone", undefined, noEmail)).toBe(true);
    expect(canSendLoginCode("phone", options({ phone_channels: [], is_phone_login_available: false }), noEmail)).toBe(
      false,
    );
  });

  it("opens on e-mail only where no phone channel is set up for any country", () => {
    const noChannelHere = options({ phone_channels: [], is_phone_login_available: false });

    expect(openingLoginMethod(options())).toBe("phone");
    // Another country has a channel: the phone form says so and offers e-mail.
    expect(openingLoginMethod(noChannelHere)).toBe("phone");
    expect(openingLoginMethod({ ...noChannelHere, configured_channels: ["email"] })).toBe("email");
    // Nothing delivers a code: the page says that sign-in is down.
    expect(
      openingLoginMethod({ ...noChannelHere, configured_channels: [], is_email_login_available: false }),
    ).toBe("phone");
  });

  it("reports sign-in as down only when nothing works anywhere", () => {
    const nothing = options({
      phone_channels: [],
      configured_channels: [],
      is_phone_login_available: false,
      is_email_login_available: false,
    });

    expect(isSignInUnavailable(nothing)).toBe(true);
    expect(isSignInUnavailable({ ...nothing, configured_channels: ["whatsapp"] })).toBe(false);
  });

  it("keeps a working chosen channel and falls back to the country's first", () => {
    expect(chooseDeliveryChannel(["sms", "telegram"], "telegram")).toBe("telegram");
    expect(chooseDeliveryChannel(["sms", "telegram"], "whatsapp")).toBe("sms");
    expect(chooseDeliveryChannel(["whatsapp"], null)).toBe("whatsapp");
    expect(chooseDeliveryChannel([], "sms")).toBeNull();
  });

  it("asks for a channel only when there was a choice", () => {
    const body = { phone_number: "555", country_hint: "GE", locale: "ka" };

    expect(withDeliveryChannel(body, "phone", ["sms", "telegram"], "telegram")).toEqual({
      ...body,
      preferred_delivery_channel: "telegram",
    });
    expect(withDeliveryChannel(body, "phone", ["sms"], "sms")).toEqual(body);
    expect(withDeliveryChannel({ email: "a@b.ge", locale: "en" }, "email", ["sms", "telegram"], "sms")).toEqual({
      email: "a@b.ge",
      locale: "en",
    });
  });
});

describe("otherDeliveryChannels", () => {
  it("offers the country's other channels on the code screen", () => {
    expect(otherDeliveryChannels(["whatsapp", "sms"], "whatsapp")).toEqual(["sms"]);
    expect(otherDeliveryChannels(["sms"], "sms")).toEqual([]);
  });
});
