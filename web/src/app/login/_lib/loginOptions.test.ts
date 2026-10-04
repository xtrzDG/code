import { describe, expect, it } from "vitest";

import {
  chooseDeliveryChannel,
  effectiveLoginMethod,
  isEmailLoginOffered,
  isSignInUnavailable,
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
    expect(effectiveLoginMethod("email", undefined)).toBe("email");
    expect(isSignInUnavailable(undefined)).toBe(false);
  });

  it("explains why phone sign-in cannot start", () => {
    expect(phoneLoginBlock(options())).toBeNull();
    expect(
      phoneLoginBlock(
        options({
          is_sign_up_restricted: true,
          is_phone_login_available: false,
        }),
      ),
    ).toBe("restricted");
    expect(
      phoneLoginBlock(
        options({ phone_channels: [], is_phone_login_available: false }),
      ),
    ).toBe("noChannels");
  });

  it("hides e-mail when it cannot deliver codes", () => {
    const noEmail = options({ is_email_login_available: false });

    expect(isEmailLoginOffered(noEmail)).toBe(false);
    expect(effectiveLoginMethod("email", noEmail)).toBe("phone");
    expect(effectiveLoginMethod("phone", noEmail)).toBe("phone");
  });

  it("reports sign-in as down only when nothing works anywhere", () => {
    const nothing = options({
      phone_channels: [],
      configured_channels: [],
      is_phone_login_available: false,
      is_email_login_available: false,
    });

    expect(isSignInUnavailable(nothing)).toBe(true);
    expect(
      isSignInUnavailable({ ...nothing, configured_channels: ["whatsapp"] }),
    ).toBe(false);
  });

  it("keeps a working chosen channel and falls back to the country's first", () => {
    expect(chooseDeliveryChannel(["sms", "telegram"], "telegram")).toBe(
      "telegram",
    );
    expect(chooseDeliveryChannel(["sms", "telegram"], "whatsapp")).toBe("sms");
    expect(chooseDeliveryChannel(["whatsapp"], null)).toBe("whatsapp");
    expect(chooseDeliveryChannel([], "sms")).toBeNull();
  });

  it("asks for a channel only when there was a choice", () => {
    const body = { phone_number: "555", country_hint: "GE", locale: "ka" };

    expect(
      withDeliveryChannel(body, "phone", ["sms", "telegram"], "telegram"),
    ).toEqual({
      ...body,
      preferred_delivery_channel: "telegram",
    });
    expect(withDeliveryChannel(body, "phone", ["sms"], "sms")).toEqual(body);
    expect(
      withDeliveryChannel(
        { email: "a@b.ge", locale: "en" },
        "email",
        ["sms", "telegram"],
        "sms",
      ),
    ).toEqual({
      email: "a@b.ge",
      locale: "en",
    });
  });
});

describe("otherDeliveryChannels", () => {
  it("offers the country's other channels on the code screen", () => {
    expect(otherDeliveryChannels(["whatsapp", "sms"], "whatsapp")).toEqual([
      "sms",
    ]);
    expect(otherDeliveryChannels(["sms"], "sms")).toEqual([]);
  });
});
