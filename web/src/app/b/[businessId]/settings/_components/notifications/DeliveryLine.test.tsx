import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { BusinessView, CurrentUserView } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { renderInLocale, textsIn } from "@/test/render";

import { DELIVERY_LABELS, type NotificationContact } from "../../_lib/notifications";
import { CHANNEL_LABELS } from "./contactTexts";
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

function show(status: "dead" | "pending" | NotificationContact, isPlatformAdmin = false) {
  const me = { user: { id: "user_1", is_platform_admin: isPlatformAdmin } } as unknown as CurrentUserView;
  renderInLocale(
    <BusinessProvider business={business} me={me}>
      <DeliveryLine status={typeof status === "string" ? contact(status, isPlatformAdmin) : status} />
    </BusinessProvider>,
    { locale: "it" },
  );
}

/** An SMS contact the platform cannot send to yet, as the API answers it to an owner. */
function smsContact(reason: "no_sender" | "not_configured", delivered?: "dead" | "delivered"): NotificationContact {
  const delivery = delivered
    ? {
        status: delivered,
        last_error: null,
        is_last_delivery_failed: delivered === "dead",
        attempted_at: 1_790_000_000_000_000,
        delivered_at: delivered === "delivered" ? 1_790_000_000_000_000 : null,
      }
    : null;
  return { channel: "sms", provider_ready: false, sms_unavailable_reason: reason, delivery } as unknown as NotificationContact;
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

  it("says SMS is not available yet while the platform's SMS number waits for the carriers", () => {
    show(smsContact("no_sender"));

    expect(screen.getByText(t("notifications.contacts.smsNotYet"))).toBeTruthy();
    expect(screen.getByText(t("notifications.contacts.smsNoSenderHint"))).toBeTruthy();
    expect(screen.queryByText(t("notifications.contacts.providerMissing"))).toBeNull();
  });

  it.each(["dead", "delivered"] as const)(
    "keeps saying why SMS is not sent yet after a notification (%s), not to contact support",
    (delivered) => {
      // Every SMS notification is refused at once while the platform's SMS
      // number waits; the stored reason reaches platform admins only.
      show(smsContact("no_sender", delivered));

      expect(screen.getByText(t("notifications.contacts.smsNotYet"))).toBeTruthy();
      expect(screen.getByText(t("notifications.contacts.smsNoSenderHint"))).toBeTruthy();
      expect(screen.queryByText(t("common.deliveryProblem"))).toBeNull();
      expect(screen.queryByText(t(DELIVERY_LABELS[delivered]))).toBeNull();
    },
  );

  it("keeps the general notice for SMS without a provider", () => {
    show(smsContact("not_configured"));

    expect(screen.getByText(t("notifications.contacts.providerMissing"))).toBeTruthy();
    expect(screen.getByText(t("notifications.contacts.providerMissingHint", { channel: t(CHANNEL_LABELS.sms) }))).toBeTruthy();
    expect(screen.queryByText(t("notifications.contacts.smsNotYet"))).toBeNull();
  });

  it("shows the latest notification of a channel without a provider once there is one", () => {
    show(smsContact("not_configured", "dead"));

    expect(screen.getByText(t(DELIVERY_LABELS.dead))).toBeTruthy();
    expect(screen.getByText(t("common.deliveryProblem"))).toBeTruthy();
    expect(screen.queryByText(t("notifications.contacts.providerMissing"))).toBeNull();
  });
});
