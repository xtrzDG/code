import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { I18nProvider, useI18n } from "./client";

const navigation = vi.hoisted(() => ({ pathname: "/en" }));

vi.mock("next/navigation", () => ({ usePathname: () => navigation.pathname }));

function Greeting() {
  const { t } = useI18n();
  return <p>{t("common.save")}</p>;
}

describe("the dictionary of a public page", () => {
  const reload = vi.fn();
  const original = window.location;

  beforeEach(() => {
    reload.mockClear();
    Object.defineProperty(window, "location", { configurable: true, value: { ...original, reload } });
  });

  afterEach(() => {
    Object.defineProperty(window, "location", { configurable: true, value: original });
  });

  it("serves the public site's pages", () => {
    navigation.pathname = "/ka/for/hotel";
    render(
      <I18nProvider locale="en" messages={{ common: { save: "Save" } }} scope="public">
        <Greeting />
      </I18nProvider>,
    );
    expect(screen.getByText("Save")).toBeTruthy();
    expect(reload).not.toHaveBeenCalled();
  });

  it("loads a cabinet page in full instead of showing it without its texts", () => {
    navigation.pathname = "/login";
    const { container } = render(
      <I18nProvider locale="en" messages={{ common: { save: "Save" } }} scope="public">
        <Greeting />
      </I18nProvider>,
    );
    expect(container.textContent).toBe("");
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it("is the whole dictionary anywhere else, whatever the address", () => {
    navigation.pathname = "/login";
    render(
      <I18nProvider locale="en" messages={{ common: { save: "Save" } }}>
        <Greeting />
      </I18nProvider>,
    );
    expect(screen.getByText("Save")).toBeTruthy();
    expect(reload).not.toHaveBeenCalled();
  });
});
