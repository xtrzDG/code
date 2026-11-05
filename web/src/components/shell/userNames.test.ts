import { describe, expect, it } from "vitest";

import { userContact, userDisplayName, userInitials } from "./userNames";

describe("the signed-in person's names", () => {
  it("show a phone number grouped, never as raw E.164", () => {
    const user = { display_name: null, phone_number: "+995555000001", email: null };
    expect(userContact(user)).toBe("+995 555 00 00 01");
    expect(userDisplayName(user)).toBe("+995 555 00 00 01");
  });

  it("prefer the name, then the phone, then the e-mail", () => {
    expect(userDisplayName({ display_name: "Nino Beridze", phone_number: "+995555000001", email: null })).toBe("Nino Beridze");
    expect(userDisplayName({ display_name: null, phone_number: null, email: "nino@cafe.example" })).toBe("nino@cafe.example");
    expect(userContact({ display_name: null, phone_number: null, email: null })).toBe("");
  });

  it("take initials from the name, else the e-mail", () => {
    expect(userInitials({ display_name: "Nino Beridze", phone_number: null, email: null })).toBe("NB");
    expect(userInitials({ display_name: null, phone_number: "+995555000001", email: "zaza@cafe.example" })).toBe("Z");
    expect(userInitials({ display_name: null, phone_number: "+995555000001", email: null })).toBe("#");
  });
});
