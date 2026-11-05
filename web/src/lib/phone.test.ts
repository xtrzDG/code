import { describe, expect, it } from "vitest";

import { formatContactAddress, formatPhone } from "./phone";

describe("formatPhone", () => {
  it("groups numbers the way their country writes them", () => {
    expect(formatPhone("+995555000001")).toBe("+995 555 00 00 01");
    expect(formatPhone("+4915112345678")).toBe("+49 1511 2345678");
    expect(formatPhone("+79161234567")).toBe("+7 916 123 45 67");
    expect(formatPhone("+12025550123")).toBe("+1 202 555 0123");
  });

  it("leaves a number that is already grouped as the country writes it", () => {
    expect(formatPhone("+995 555 00 00 01")).toBe("+995 555 00 00 01");
  });

  it("returns anything else unchanged", () => {
    expect(formatPhone("")).toBe("");
    expect(formatPhone(null)).toBe("");
    expect(formatPhone("owner@example.com")).toBe("owner@example.com");
    expect(formatPhone("@nino_cafe")).toBe("@nino_cafe");
    expect(formatPhone("555000001")).toBe("555000001");
    expect(formatPhone("+12")).toBe("+12");
  });
});

describe("formatContactAddress", () => {
  it("formats phones by channel and keeps e-mails and Telegram chats", () => {
    expect(formatContactAddress("whatsapp", "+995555000001")).toBe("+995 555 00 00 01");
    expect(formatContactAddress("sms", "+995555000001")).toBe("+995 555 00 00 01");
    expect(formatContactAddress("email", "owner@example.com")).toBe("owner@example.com");
    expect(formatContactAddress("telegram", "123456789")).toBe("123456789");
  });
});
