import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { queryCache } from "@/api/queryCache";
import { queryKeys } from "@/api/queryKeys";
import { answerGet, failure, ok, pending } from "@/test/fakeApi";
import { Providers } from "@/test/render";

import { emailOnly, everyMethod, nothingDelivers, phoneOnly } from "./loginFixtures";
import type { LoginOptions } from "./loginOptions";
import { type Destination, useDestination } from "./useDestination";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));

const COUNTRIES = {
  display_language: "en",
  countries: [
    { country_code: "US", display_name: "United States", english_name: "United States", calling_code: 1, onboarding_status: "supported" },
    { country_code: "IT", display_name: "Italy", english_name: "Italy", calling_code: 39, onboarding_status: "supported" },
  ],
};

/** An API answer the test gives when it says so. */
function later(): { promise: Promise<unknown>; give: (answer: Promise<unknown>) => void } {
  let give: (answer: Promise<unknown>) => void = () => undefined;
  const promise = new Promise<unknown>((resolve) => {
    give = resolve;
  });
  return { promise, give };
}

/** The countries and the sign-in options of no country, the United States and Italy, each answered when the test says so. */
function answersInTurn() {
  const answers = { countries: later(), none: later(), US: later(), IT: later() };
  answerGet((path, init) => {
    if (path === "/v1/catalog/countries") {
      return answers.countries.promise;
    }
    if (path !== "/v1/auth/login-options") {
      return pending();
    }
    const country = init.params?.query?.country_code;
    return (country === "US" || country === "IT" ? answers[country] : answers.none).promise;
  });
  return answers;
}

/** The destination of a page opened on e-mail and of one opened on phone. */
function renderDestinations() {
  const wrapper = ({ children }: { children: ReactNode }) => <Providers>{children}</Providers>;
  return renderHook(() => ({ email: useDestination("email"), phone: useDestination("phone") }), { wrapper });
}

/** What is the same for every country, and whether each form can send. */
function shared({ email, phone }: { email: Destination; phone: Destination }) {
  return {
    isEmailOffered: email.isEmailOffered,
    isUnavailable: email.isUnavailable,
    termsVersion: email.termsVersion,
    privacyVersion: email.privacyVersion,
    phoneBlock: phone.phoneBlock,
    canSendEmail: email.canSend,
    canSendPhone: phone.canSend,
  };
}

describe("useDestination", () => {
  beforeEach(() => {
    queryCache.clear();
  });

  it.each([
    ["by e-mail only", emailOnly],
    ["to phones only", phoneOnly],
    ["nowhere", nothingDelivers],
  ])(
    "keeps what is the same for every country, where codes go %s, while a country's answer loads and after it failed",
    async (_, deployment) => {
      const answers = answersInTurn();
      const { result } = renderDestinations();

      answers.none.give(ok(deployment));
      await waitFor(() => expect(result.current.email.termsVersion).toBe(deployment.terms_version));
      const answered = shared(result.current);

      // The countries come: the guessed country's own answer loads.
      answers.countries.give(ok(COUNTRIES));
      await waitFor(() => expect(result.current.email.countryCode).toBe("US"));
      expect(shared(result.current)).toEqual(answered);

      // It fails (the API's request limit): what every country shares stays.
      answers.US.give(failure(429, { error: { code: "rate_limited", message: "Too many requests." } }));
      await waitFor(() => expect(queryCache.get(queryKeys.auth.loginOptions("US")).error).not.toBeNull());
      expect(shared(result.current)).toEqual(answered);
    },
  );

  it("takes a country's phone channels and blocks from that country's own answer only", async () => {
    const twoChannels: LoginOptions = {
      ...everyMethod,
      configured_channels: ["email", "sms", "whatsapp"],
      phone_channels: ["sms", "whatsapp"],
    };
    const answers = answersInTurn();
    const { result } = renderDestinations();
    answers.none.give(ok(twoChannels));
    await waitFor(() => expect(result.current.phone.phoneChannels).toEqual(["sms", "whatsapp"]));
    act(() => result.current.phone.setChannel("whatsapp"));
    expect(result.current.phone.deliveryChannel).toBe("whatsapp");

    // The guessed country's answer loads: no other country's channels meanwhile.
    answers.countries.give(ok(COUNTRIES));
    await waitFor(() => expect(result.current.phone.countryCode).toBe("US"));
    expect(result.current.phone).toMatchObject({ phoneChannels: [], deliveryChannel: null, phoneBlock: null, canSend: true });

    answers.US.give(
      ok({ ...twoChannels, country_code: "US", phone_channels: [], is_phone_login_available: false, is_sign_up_restricted: true }),
    );
    await waitFor(() => expect(result.current.phone.phoneBlock).toBe("restricted"));
    expect(result.current.phone.canSend).toBe(false);

    // Another country: the United States' block does not follow it.
    act(() => result.current.phone.setCountry("IT"));
    expect(result.current.phone).toMatchObject({ phoneBlock: null, phoneChannels: [], canSend: true });

    answers.IT.give(ok({ ...twoChannels, country_code: "IT", phone_channels: ["whatsapp"] }));
    await waitFor(() => expect(result.current.phone.phoneChannels).toEqual(["whatsapp"]));
    expect(result.current.phone.deliveryChannel).toBe("whatsapp");
  });
});
