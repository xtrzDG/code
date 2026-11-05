import { screen, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderInLocale, textsIn } from "@/test/render";

import { AccessibilityScreen } from "./AccessibilityScreen";
import { loadLegalOverview, loadSupportContacts } from "./legalData";

vi.mock("@/i18n/server", async () => {
  const { textsIn: texts } = await import("@/test/render");
  return { getI18n: vi.fn(async () => texts("it")) };
});
vi.mock("./legalData", () => ({ loadLegalOverview: vi.fn(), loadSupportContacts: vi.fn() }));
// The site's header and footer (and the cookie banner) are not this page's subject.
vi.mock("../LandingHeader", () => ({ LandingHeader: () => null }));
vi.mock("../LandingFooter", () => ({ LandingFooter: () => null }));
vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

const { t } = textsIn("it");

async function renderStatement(): Promise<void> {
  renderInLocale(await AccessibilityScreen({ locale: "it" }), { locale: "it" });
}

beforeEach(() => {
  vi.mocked(loadLegalOverview).mockResolvedValue(null);
  vi.mocked(loadSupportContacts).mockResolvedValue(null);
});

describe("the accessibility statement", () => {
  it("follows AgID's model: status, limitations, method and date, feedback, enforcement", async () => {
    await renderStatement();

    expect(screen.getByRole("heading", { level: 1, name: t("accessibility.title") })).toBeTruthy();
    for (const title of ["statusTitle", "limitationsTitle", "methodTitle", "feedbackTitle", "enforcementTitle", "technologiesTitle"] as const) {
      expect(screen.getByRole("heading", { level: 2, name: t(`accessibility.${title}`) }), title).toBeTruthy();
    }
    expect(screen.getByText(/WCAG\) 2\.2 al livello AA/)).toBeTruthy();
    expect(screen.getByText(/parzialmente conforme/i)).toBeTruthy();
    expect(screen.getAllByRole("listitem").filter((item) => item.closest("[data-testid='accessibility-statement']"))).toHaveLength(4);
    expect(screen.getByText(/redatta il 3 novembre 2026/)).toBeTruthy();
    expect(screen.getByRole("link", { name: t("accessibility.enforcementLink") }).getAttribute("href")).toBe("https://form.agid.gov.it/");
  });

  it("names the provider and its support e-mail when the platform has them, else the contact page", async () => {
    await renderStatement();
    expect(screen.getByText(new RegExp(`^${t("accessibility.operatorFallback")} vuole`))).toBeTruthy();
    const statement = within(screen.getByTestId("accessibility-statement"));
    expect(statement.getByRole("link", { name: t("accessibility.contactLink") }).getAttribute("href")).toBe("/it/contact");
  });

  it("uses the operator's name and the support mailbox once they are set", async () => {
    vi.mocked(loadLegalOverview).mockResolvedValue({
      is_draft: true,
      dpa_version: "2026-10-06",
      operator: { legal_name: "Officina Assistenti S.r.l.", email: "legal@example.com" },
    } as never);
    vi.mocked(loadSupportContacts).mockResolvedValue({ email: "help@example.com" } as never);

    await renderStatement();

    expect(screen.getByText(/^Officina Assistenti S\.r\.l\. vuole/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Scrivi a help@example.com." }).getAttribute("href")).toBe("mailto:help@example.com");
  });
});
