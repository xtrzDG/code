import { isValidElement, type ReactElement, type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { LoginMethod } from "@/lib/countries";
import { HOME_PATH } from "@/lib/navigation";

import { loadOpeningLoginMethod } from "./_lib/openingMethod";
import { LoginScreen } from "./LoginScreen";
import LoginPage from "./page";

// The page's own work is what it hands to the screen: neither part renders here.
vi.mock("./_lib/openingMethod", () => ({ loadOpeningLoginMethod: vi.fn() }));
vi.mock("./LoginScreen", () => ({ LoginScreen: () => null }));
vi.mock("@/components/shell/TopBar", () => ({ TopBar: () => null }));
vi.mock("@/i18n/server", () => ({ getI18n: vi.fn() }));

type Query = Record<string, string | string[] | undefined>;
type ScreenProps = Parameters<typeof LoginScreen>[0];

/** The first element of the given type in a rendered tree. */
function findElement(node: ReactNode, type: unknown): ReactElement | null {
  if (Array.isArray(node)) {
    for (const child of node as ReactNode[]) {
      const found = findElement(child, type);
      if (found) {
        return found;
      }
    }
    return null;
  }
  if (!isValidElement(node)) {
    return null;
  }
  if (node.type === type) {
    return node;
  }
  return findElement((node.props as { children?: ReactNode }).children, type);
}

/** What the page hands to the sign-in screen for a request's query. */
async function screenProps(query: Query = {}): Promise<ScreenProps> {
  const page = await LoginPage({ params: Promise.resolve({}), searchParams: Promise.resolve(query) });
  const screen = findElement(page, LoginScreen);
  if (!screen) {
    throw new Error("The page renders no sign-in screen");
  }
  return screen.props as ScreenProps;
}

function serverChooses(method: LoginMethod) {
  vi.mocked(loadOpeningLoginMethod).mockResolvedValue(method);
}

describe("the sign-in page", () => {
  beforeEach(() => {
    vi.mocked(loadOpeningLoginMethod).mockReset();
    serverChooses("phone");
  });

  it.each<LoginMethod>(["email", "phone"])("opens the screen on the form the server chose: %s", async (method) => {
    serverChooses(method);

    expect((await screenProps()).openingMethod).toBe(method);
    expect(loadOpeningLoginMethod).toHaveBeenCalledTimes(1);
  });

  it("sends the visitor on to the page they came for, and never off the site", async () => {
    expect((await screenProps({ next: "/businesses/b1/calls" })).next).toBe("/businesses/b1/calls");
    expect((await screenProps()).next).toBe(HOME_PATH);
    expect((await screenProps({ next: "//evil.example/steal" })).next).toBe(HOME_PATH);
    expect((await screenProps({ next: ["/a", "/b"] })).next).toBe(HOME_PATH);
  });

  it("says that the session ended only when the visitor was sent here for that", async () => {
    expect((await screenProps({ reason: "expired" })).sessionExpired).toBe(true);
    expect((await screenProps()).sessionExpired).toBe(false);
    expect((await screenProps({ reason: "other" })).sessionExpired).toBe(false);
  });
});
