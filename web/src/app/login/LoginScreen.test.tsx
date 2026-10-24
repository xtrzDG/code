import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { startLogin, verifyLogin } from "@/api/auth";
import type * as AuthModule from "@/api/auth";
import { ApiError } from "@/api/errors";
import { queryCache } from "@/api/queryCache";
import type { OtpChallengeView } from "@/api/types";
import { answerGet, ok, pending } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

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

function signInOptions() {
  answerGet((path) => {
    if (path === "/v1/auth/login-options") {
      return ok({
        configured_channels: ["email", "sms"],
        is_email_login_available: true,
        is_phone_login_available: true,
        is_sign_up_restricted: false,
        phone_channels: ["sms"],
        terms_version: "2026-09-01",
        privacy_version: "2026-09-01",
      });
    }
    return path === "/v1/catalog/countries" ? ok({ countries: [] }) : pending();
  });
}

async function chooseEmail(user: ReturnType<typeof userEvent.setup>) {
  renderInLocale(<LoginScreen next="/businesses" sessionExpired={false} />);
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
