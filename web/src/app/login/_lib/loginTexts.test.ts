import { describe, expect, it } from "vitest";

import { CODE_LENGTH, CodeSchema, DELIVERY_CHANNEL_LABELS, EmailSchema, PhoneSchema } from "./loginTexts";

describe("sign-in input rules", () => {
  it("accept a phone number and trim it", () => {
    const parsed = PhoneSchema.safeParse("  +995 555 12 34 56 ");

    expect(parsed.success).toBe(true);
    expect(parsed.data).toBe("+995 555 12 34 56");
  });

  it("explain an empty or malformed phone number", () => {
    expect(PhoneSchema.safeParse("   ").error?.issues[0]?.message).toBe("auth.errors.phoneRequired");
    expect(PhoneSchema.safeParse("call me").error?.issues[0]?.message).toBe("auth.errors.phoneInvalid");
  });

  it("check e-mail addresses", () => {
    expect(EmailSchema.safeParse(" owner@example.com ").data).toBe("owner@example.com");
    expect(EmailSchema.safeParse("owner@").error?.issues[0]?.message).toBe("auth.errors.emailInvalid");
  });

  it("take codes of exactly six digits", () => {
    expect(CODE_LENGTH).toBe(6);
    expect(CodeSchema.safeParse("123456").success).toBe(true);
    expect(CodeSchema.safeParse("12345").error?.issues[0]?.message).toBe("auth.errors.codeInvalid");
    expect(CodeSchema.safeParse("12a456").success).toBe(false);
  });

  it("label every delivery channel", () => {
    expect(Object.values(DELIVERY_CHANNEL_LABELS)).toEqual([
      "auth.deliveryChannels.sms",
      "auth.deliveryChannels.whatsapp",
      "auth.deliveryChannels.telegram",
      "auth.deliveryChannels.email",
    ]);
  });
});
