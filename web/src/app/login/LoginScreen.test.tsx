import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { startLogin, verifyLogin } from "@/api/auth";
import type * as AuthModule from "@/api/auth";
import { ApiError } from "@/api/errors";
import { queryCache } from "@/api/queryCache";
import type { OtpChallengeView } from "@/api/types";
import { renderInLocale, textsIn } from "@/test/render";

import {
  emailOnly,
  everyMethod,
  nothingDelivers,
  phoneOnly,
  signInOptions,
  signInOptionsLater,
} from "./_lib/loginFixtures";
import { LoginScreen } from "./LoginScreen";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));
vi.mock("@/api/auth", async (importOriginal) => ({
  ...(await importOriginal<typeof AuthModule>()),
  startLogin: vi.fn(),
  verifyLogin: vi.fn(),
}));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

const { t } = textsIn("en");

const challenge: OtpChallengeView = {
  challenge_id: "challenge_1",
  delivery_channel: "email",
  expires_in_seconds: 600,
  locale: "en",
  login_method: "email",
  masked_destination: "o***@example.com",
};

async function chooseEmail(user: ReturnType<typeof userEvent.setup>) {
  renderInLocale(<LoginScreen next="/businesses" sessionExpired={false} openingMethod="phone" />);
  await user.click(await screen.findByRole("radio", { name: t("auth.methodEmail") }));
  return screen.getByRole("textbox", { name: t("auth.email") });
}

describe("LoginScreen: e-mail and code", () => {
  beforeEach(() => {
    queryCache.clear();
    signInOptions();
  });

  it("refuses an address that is not one, before asking the API", async () => {
    const user = userEvent.setup();
    const email = await chooseEmail(user);

    await user.type(email, "owner.example.com");
    await user.click(screen.getByRole("button", { name: t("auth.sendCode") }));

    expect(email.getAttribute("aria-invalid")).toBe("true");
    expect(screen.getByText(t("auth.errors.emailInvalid"))).toBeTruthy();
    expect(startLogin).not.toHaveBeenCalled();

    // Typing again clears the error.
    await user.type(email, "x");
    expect(email.hasAttribute("aria-invalid")).toBe(false);
  });

  it("sends the code to the address and moves to the code step with the field focused", async () => {
    const user = userEvent.setup();
    vi.mocked(startLogin).mockResolvedValue(challenge);
    const email = await chooseEmail(user);

    await user.type(email, "owner@example.com");
    await user.click(screen.getByRole("button", { name: t("auth.sendCode") }));

    expect(await screen.findByRole("heading", { name: t("auth.codeTitle") })).toBeTruthy();
    expect(vi.mocked(startLogin).mock.calls[0]?.[0]).toMatchObject({ email: "owner@example.com" });
    const code = screen.getByRole("textbox", { name: t("auth.code") });
    await waitFor(() => expect(document.activeElement).toBe(code));
    expect(screen.getByText(/o\*\*\*@example\.com/)).toBeTruthy();
  });

  it("checks the code as its last digit is typed and says when it is wrong", async () => {
    const user = userEvent.setup();
    vi.mocked(startLogin).mockResolvedValue(challenge);
    vi.mocked(verifyLogin).mockRejectedValue(new ApiError({ status: 401, code: "authentication_required" }));
    const email = await chooseEmail(user);
    await user.type(email, "owner@example.com");
    await user.click(screen.getByRole("button", { name: t("auth.sendCode") }));
    const code = await screen.findByRole("textbox", { name: t("auth.code") });

    await user.type(code, "12 34 56");

    expect(vi.mocked(verifyLogin).mock.calls[0]?.[0]).toMatchObject({ challenge_id: "challenge_1", code: "123456" });
    expect(await screen.findByText(t("auth.errors.wrongCode"))).toBeTruthy();
    expect(code.getAttribute("aria-invalid")).toBe("true");
  });

  it("goes back to the address step to change it", async () => {
    const user = userEvent.setup();
    vi.mocked(startLogin).mockResolvedValue(challenge);
    const email = await chooseEmail(user);
    await user.type(email, "owner@example.com");
    await user.click(screen.getByRole("button", { name: t("auth.sendCode") }));

    await user.click(await screen.findByRole("button", { name: t("auth.changeDestination") }));

    expect(screen.getByRole("heading", { name: t("auth.title") })).toBeTruthy();
  });
});

describe("LoginScreen: the method it opens on", () => {
  beforeEach(() => {
    queryCache.clear();
  });

  const phoneField = () => screen.queryByRole<HTMLInputElement>("textbox", { name: t("auth.phone") });
  const emailField = () => screen.queryByRole<HTMLInputElement>("textbox", { name: t("auth.email") });
  const isChecked = (name: string) => screen.getByRole<HTMLInputElement>("radio", { name }).checked;
  const sendButton = () => screen.getByRole<HTMLButtonElement>("button", { name: t("auth.sendCode") });

  it("opens on e-mail when the server says so, before the browser has asked anything", () => {
    signInOptionsLater(emailOnly);
    renderInLocale(<LoginScreen next="/businesses" sessionExpired={false} openingMethod="email" />);

    expect(emailField()).toBeTruthy();
    expect(isChecked(t("auth.methodEmail"))).toBe(true);
    expect(phoneField()).toBeNull();
  });

  it("opens on phone when the server says so", () => {
    signInOptionsLater(everyMethod);
    renderInLocale(<LoginScreen next="/businesses" sessionExpired={false} openingMethod="phone" />);

    expect(phoneField()).toBeTruthy();
    expect(isChecked(t("auth.methodPhone"))).toBe(true);
    expect(emailField()).toBeNull();
  });

  it("never takes the phone form from a visitor who is using it", async () => {
    const user = userEvent.setup();
    const answerOptions = signInOptionsLater(emailOnly);
    renderInLocale(<LoginScreen next="/businesses" sessionExpired={false} openingMethod="phone" />);
    const phone = phoneField();
    if (!phone) {
      throw new Error("The phone field is missing.");
    }
    await user.type(phone, "12");
    await user.click(screen.getByRole("button", { name: t("auth.sendCode") }));
    expect(phone.getAttribute("aria-invalid")).toBe("true");
    await user.click(phone);

    // The answer says that codes go by e-mail only: the page explains and offers, the form stays.
    answerOptions();

    expect(await screen.findByText(t("loginOptions.noPhoneChannels"))).toBeTruthy();
    expect(phoneField()).toBe(phone);
    expect(phone.value).toBe("12");
    expect(document.activeElement).toBe(phone);
    expect(phone.getAttribute("aria-invalid")).toBe("true");
    expect(emailField()).toBeNull();
    expect(startLogin).not.toHaveBeenCalled();
  });

  it("keeps the phone form a visitor chose, with its way back to e-mail", async () => {
    const user = userEvent.setup();
    signInOptions(emailOnly);
    renderInLocale(<LoginScreen next="/businesses" sessionExpired={false} openingMethod="email" />);

    await user.click(screen.getByRole("radio", { name: t("auth.methodPhone") }));

    expect(phoneField()).toBeTruthy();
    expect(await screen.findByText(t("loginOptions.noPhoneChannels"))).toBeTruthy();
    // The switch keeps the focus it was given.
    expect(document.activeElement).toBe(screen.getByRole("radio", { name: t("auth.methodPhone") }));

    await user.click(screen.getByRole("button", { name: t("loginOptions.useEmail") }));

    expect(emailField()).toBeTruthy();
    expect(phoneField()).toBeNull();
    // The button left with the phone form: focus is in the field that took its place.
    expect(document.activeElement).toBe(emailField());
  });

  it("never takes the e-mail form from a visitor who is using it", async () => {
    const user = userEvent.setup();
    const answerOptions = signInOptionsLater(phoneOnly);
    renderInLocale(<LoginScreen next="/businesses" sessionExpired={false} openingMethod="phone" />);
    // Nothing has answered yet, so the switch still offers e-mail.
    await user.click(screen.getByRole("radio", { name: t("auth.methodEmail") }));
    const email = emailField();
    if (!email) {
      throw new Error("The e-mail field is missing.");
    }
    await user.type(email, "owner");
    await user.click(sendButton());
    expect(email.getAttribute("aria-invalid")).toBe("true");
    await user.click(email);

    // The answer says that e-mail cannot deliver: the page explains and offers, the form stays.
    answerOptions();

    expect(await screen.findByText(t("loginOptions.noEmail"))).toBeTruthy();
    expect(emailField()).toBe(email);
    expect(email.value).toBe("owner");
    expect(document.activeElement).toBe(email);
    expect(email.getAttribute("aria-invalid")).toBe("true");
    expect(screen.getByText(t("auth.errors.emailInvalid"))).toBeTruthy();
    expect(phoneField()).toBeNull();
    // The switch stays under the visitor, and no code can be asked for.
    expect(isChecked(t("auth.methodEmail"))).toBe(true);
    expect(sendButton().disabled).toBe(true);
    await user.type(email, "@example.com{Enter}");
    expect(email.value).toBe("owner@example.com");
    expect(startLogin).not.toHaveBeenCalled();
  });

  it("leads from an e-mail form that cannot deliver to the phone form", async () => {
    const user = userEvent.setup();
    signInOptions(phoneOnly);
    renderInLocale(<LoginScreen next="/businesses" sessionExpired={false} openingMethod="email" />);

    await user.click(await screen.findByRole("button", { name: t("loginOptions.usePhone") }));

    expect(phoneField()).toBeTruthy();
    expect(document.activeElement).toBe(phoneField());
    expect(emailField()).toBeNull();
    expect(screen.queryByText(t("loginOptions.noEmail"))).toBeNull();
    // E-mail cannot deliver: the switch went with its form.
    expect(screen.queryByRole("radio", { name: t("auth.methodEmail") })).toBeNull();
    expect(sendButton().disabled).toBe(false);
  });

  it("says once that sign-in is down when nothing delivers a code", async () => {
    signInOptions(nothingDelivers);
    renderInLocale(<LoginScreen next="/businesses" sessionExpired={false} openingMethod="email" />);

    expect(await screen.findByText(t("loginOptions.nothingAvailable"))).toBeTruthy();
    expect(screen.queryByText(t("loginOptions.noEmail"))).toBeNull();
    expect(emailField()).toBeTruthy();
    expect(sendButton().disabled).toBe(true);
  });

  it("names the method of its form in the HTML, for the smoke test of a deployment", async () => {
    const user = userEvent.setup();
    signInOptions();
    const { container } = renderInLocale(
      <LoginScreen next="/businesses" sessionExpired={false} openingMethod="email" />,
    );
    const methods = () =>
      Array.from(container.querySelectorAll("[data-login-method]"), (form) => form.getAttribute("data-login-method"));

    // scripts/smoke.sh looks for exactly one `data-login-method="..."`.
    expect(methods()).toEqual(["email"]);

    await user.click(screen.getByRole("radio", { name: t("auth.methodPhone") }));

    expect(methods()).toEqual(["phone"]);
  });
});
