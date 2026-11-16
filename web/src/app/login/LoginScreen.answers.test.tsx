import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import { queryKeys } from "@/api/queryKeys";
import { answerGet, ok, pending } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import { emailOnly, phoneOnly, signInOptionsLater } from "./_lib/loginFixtures";
import type { LoginOptions } from "./_lib/loginOptions";
import { LoginScreen } from "./LoginScreen";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));
vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: ReactNode }) => <a href={href}>{children}</a>,
}));

const { t } = textsIn("en");

/** An answer the test gives when it says so. */
function later<T>(): { promise: Promise<T>; give: (value: T) => void } {
  let give: (value: T) => void = () => undefined;
  const promise = new Promise<T>((resolve) => {
    give = resolve;
  });
  return { promise, give };
}

/** The answer for no country, the countries, then the United States' answer, each when the test says so. */
function answersInTurn() {
  const noCountry = later<LoginOptions>();
  const countries = later<unknown>();
  const unitedStates = later<LoginOptions>();
  answerGet((path, init) => {
    if (path === "/v1/catalog/countries") {
      return countries.promise.then(ok);
    }
    if (path !== "/v1/auth/login-options") {
      return pending();
    }
    return (init.params?.query?.country_code === "US" ? unitedStates : noCountry).promise.then(ok);
  });
  return {
    noCountry: noCountry.give,
    /** The countries come: the browser asks again for the guessed country. */
    countries: async () => {
      countries.give({
        display_language: "en",
        countries: [{ country_code: "US", display_name: "United States", english_name: "United States", calling_code: 1, onboarding_status: "supported" }],
      });
      await waitFor(() =>
        expect(vi.mocked(api.GET)).toHaveBeenCalledWith("/v1/auth/login-options", {
          params: { query: { country_code: "US" } },
        }),
      );
    },
    unitedStates: async (options: LoginOptions) => {
      unitedStates.give(options);
      await waitFor(() => expect(queryCache.get(queryKeys.auth.loginOptions("US")).data).toBeDefined());
    },
  };
}

const emailField = () => screen.queryByRole<HTMLInputElement>("textbox", { name: t("auth.email") });
const phoneField = () => screen.queryByRole<HTMLInputElement>("textbox", { name: t("auth.phone") });
const sendButton = () => screen.getByRole<HTMLButtonElement>("button", { name: t("auth.sendCode") });

describe("LoginScreen: the browser's answers", () => {
  beforeEach(() => {
    queryCache.clear();
  });

  it("keeps the e-mail notice while the chosen country's own answer loads", async () => {
    const user = userEvent.setup();
    const sent = vi.spyOn(globalThis, "fetch");
    const answers = answersInTurn();
    renderInLocale(<LoginScreen next="/businesses" sessionExpired={false} openingMethod="phone" />);
    await user.click(screen.getByRole("radio", { name: t("auth.methodEmail") }));
    await user.type(emailField() as HTMLInputElement, "owner@example.com");
    const notice = () => screen.queryByText(t("loginOptions.noEmail"));

    // The answer for no country: e-mail cannot deliver.
    answers.noCountry(phoneOnly);
    expect(await screen.findByText(t("loginOptions.noEmail"))).toBeTruthy();
    expect(sendButton().disabled).toBe(true);

    await answers.countries();
    // While it loads, the notice stays and nothing can be sent.
    expect(notice()).toBeTruthy();
    expect(sendButton().disabled).toBe(true);
    await user.type(emailField() as HTMLInputElement, "{Enter}");

    await answers.unitedStates({ ...phoneOnly, country_code: "US" });
    expect(notice()).toBeTruthy();
    expect(phoneField()).toBeNull();
    expect(sendButton().disabled).toBe(true);
    expect(emailField()?.value).toBe("owner@example.com");
    expect(sent).not.toHaveBeenCalled();
  });

  it("keeps the phone notice while the chosen country's own answer loads, where codes go by e-mail only", async () => {
    const user = userEvent.setup();
    const sent = vi.spyOn(globalThis, "fetch");
    const answers = answersInTurn();
    renderInLocale(<LoginScreen next="/businesses" sessionExpired={false} openingMethod="email" />);
    await user.click(screen.getByRole("radio", { name: t("auth.methodPhone") }));
    await user.type(phoneField() as HTMLInputElement, "2025550123");
    const notice = () => screen.queryByText(t("loginOptions.noPhoneChannels"));
    const useEmail = () => screen.queryByRole("button", { name: t("loginOptions.useEmail") });

    // The answer for no country: codes go by e-mail only.
    answers.noCountry(emailOnly);
    expect(await screen.findByText(t("loginOptions.noPhoneChannels"))).toBeTruthy();
    expect(sendButton().disabled).toBe(true);

    await answers.countries();
    // While it loads, the notice and its way to e-mail stay, and nothing can be sent.
    expect(notice()).toBeTruthy();
    expect(useEmail()).toBeTruthy();
    expect(sendButton().disabled).toBe(true);
    await user.type(phoneField() as HTMLInputElement, "{Enter}");

    await answers.unitedStates({ ...emailOnly, country_code: "US" });
    expect(notice()).toBeTruthy();
    expect(useEmail()).toBeTruthy();
    expect(sendButton().disabled).toBe(true);
    expect(phoneField()?.value).toBe("2025550123");
    expect(sent).not.toHaveBeenCalled();
  });

  it("gives focus to the phone field when the switch goes with the e-mail form", async () => {
    const user = userEvent.setup();
    const answerOptions = signInOptionsLater(phoneOnly);
    renderInLocale(<LoginScreen next="/businesses" sessionExpired={false} openingMethod="phone" />);
    await user.click(screen.getByRole("radio", { name: t("auth.methodEmail") }));
    answerOptions();
    expect(await screen.findByText(t("loginOptions.noEmail"))).toBeTruthy();

    await user.click(screen.getByRole("radio", { name: t("auth.methodPhone") }));

    // E-mail cannot deliver: the switch left with the e-mail form, focus did not.
    expect(screen.queryByRole("radio", { name: t("auth.methodPhone") })).toBeNull();
    expect(document.activeElement).toBe(phoneField());
  });

  it("gives focus to the phone field when an answer takes the switch away from under it", async () => {
    const user = userEvent.setup();
    const answerOptions = signInOptionsLater(phoneOnly);
    renderInLocale(<LoginScreen next="/businesses" sessionExpired={false} openingMethod="phone" />);
    // Nothing has answered yet: the switch is there, and focus is on it.
    await user.click(screen.getByRole("radio", { name: t("auth.methodPhone") }));
    expect(document.activeElement).toBe(screen.getByRole("radio", { name: t("auth.methodPhone") }));

    // The answer says that e-mail cannot deliver: the switch goes.
    answerOptions();
    await waitFor(() => expect(screen.queryByRole("radio", { name: t("auth.methodPhone") })).toBeNull());

    expect(document.activeElement).toBe(phoneField());
  });

  it.each([
    ["e-mail", phoneOnly, "email", "loginOptions.usePhone"],
    ["phone", emailOnly, "phone", "loginOptions.useEmail"],
  ] as const)("lets the %s notice's button grow with a label that wraps", async (_, options, openingMethod, label) => {
    signInOptionsLater(options)();
    renderInLocale(<LoginScreen next="/businesses" sessionExpired={false} openingMethod={openingMethod} />);

    const classes = (await screen.findByRole("button", { name: t(label) })).className.split(" ");

    expect(classes).toEqual(expect.arrayContaining(["h-auto", "min-h-8"]));
    expect(classes).not.toContain("h-8");
  });
});
