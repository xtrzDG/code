import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { BusinessView, CurrentUserView } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { renderInLocale, textsIn } from "@/test/render";

import type { NotificationContact } from "../../_lib/notifications";
import { DeliveryLine } from "./DeliveryLine";

const business = { id: "business_1", viewer_role: "owner", status: "live", currency_code: "EUR", timezone: "Europe/Rome" } as unknown as BusinessView;
const RAW = "Too many notifications to this recipient in the last hour; this one was not sent.";

/** As the API answers: the provider's words only for platform admins (API-05). */
function contact(status: "dead" | "pending", isPlatformAdmin: boolean): NotificationContact {
  return {
    channel: "telegram",
    provider_ready: true,
    delivery: {
      status,
      last_error: isPlatformAdmin ? RAW : null,
      is_last_delivery_failed: true,
      attempted_at: 1_790_000_000_000_000,
      delivered_at: null,
    },
  } as unknown as NotificationContact;
}

function show(status: "dead" | "pending", isPlatformAdmin = false) {
  const me = { user: { id: "user_1", is_platform_admin: isPlatformAdmin } } as unknown as CurrentUserView;
  renderInLocale(
    <BusinessProvider business={business} me={me}>
      <DeliveryLine status={contact(status, isPlatformAdmin)} />
    </BusinessProvider>,
    { locale: "it" },
  );
}

describe("DeliveryLine", () => {
  const { t } = textsIn("it");

  it("tells the owner in their language that a notification did not get through", () => {
    show("dead");

    expect(screen.getByText(t("common.deliveryProblem"))).toBeTruthy();
    expect(screen.queryByText(RAW)).toBeNull();
  });

  it("says a failed attempt is tried again while it is pending", () => {
    show("pending");

    expect(screen.getByText(t("notifications.contacts.retrying"))).toBeTruthy();
  });

  it("adds the server's reason for platform admins", () => {
    show("dead", true);

    expect(screen.getByText(RAW)).toBeTruthy();
  });
});
