import { renderHook, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import type { BusinessView, CurrentUserView } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { renderInLocale, textsIn } from "@/test/render";

import { DeliveryProblem, useAdminErrorDetail } from "./DeliveryProblem";

const RAW = "TELEGRAM_PLATFORM_BOT_TOKEN is not configured.";
const business = { id: "business_1", viewer_role: "owner", status: "live", currency_code: "EUR" } as unknown as BusinessView;

function asViewer(isPlatformAdmin: boolean) {
  const me = { user: { id: "user_1", is_platform_admin: isPlatformAdmin } } as unknown as CurrentUserView;
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <BusinessProvider business={business} me={me}>
        {children}
      </BusinessProvider>
    );
  };
}

describe("DeliveryProblem", () => {
  it.each(["en", "it"] as const)("tells owners in plain words, without the server's raw error (%s)", (locale) => {
    const Owner = asViewer(false);
    renderInLocale(
      <Owner>
        <DeliveryProblem error={RAW} />
      </Owner>,
      { locale },
    );

    expect(screen.getByText(textsIn(locale).t("common.deliveryProblem"))).toBeTruthy();
    expect(document.body.textContent).not.toContain("TELEGRAM");
  });

  it("adds the raw error for platform admins", () => {
    const Admin = asViewer(true);
    renderInLocale(
      <Admin>
        <DeliveryProblem error={RAW} message="The last one did not arrive." />
      </Admin>,
    );

    expect(screen.getByText("The last one did not arrive.")).toBeTruthy();
    expect(screen.getByText(RAW)).toBeTruthy();
  });

  it("gives a toast its raw description only for platform admins, and never outside a business", () => {
    expect(renderHook(() => useAdminErrorDetail(), { wrapper: asViewer(true) }).result.current(RAW)).toBe(RAW);
    expect(renderHook(() => useAdminErrorDetail(), { wrapper: asViewer(false) }).result.current(RAW)).toBeNull();
    expect(renderHook(() => useAdminErrorDetail()).result.current(RAW)).toBeNull();
    expect(renderHook(() => useAdminErrorDetail(), { wrapper: asViewer(true) }).result.current(null)).toBeNull();
  });
});
