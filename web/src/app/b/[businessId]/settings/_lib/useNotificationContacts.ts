"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import type { ManagerContact } from "./contacts";
import { contactCheckOutcome, type NotificationContact } from "./notifications";

const identity = (contact: Pick<ManagerContact, "channel" | "address">) => `${contact.channel}:${contact.address}`;

/**
 * How notifications reach each staff contact: whether the platform has a
 * provider for the channel, how the latest one went, the Telegram
 * @username of a linked chat; and the owner's "Send a test", whose answer
 * says whether it arrived.
 */
export function useNotificationContacts() {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const key = queryKeys.notifications.contacts(business.id);
  const list = useQuery(key, () =>
    api.GET("/v1/businesses/{business_id}/notification-contacts", { params: { path: { business_id: business.id } } }),
  );
  const [checking, setChecking] = useState<string | null>(null);
  const check = useMutation(
    (contact: NotificationContact) =>
      api.POST("/v1/businesses/{business_id}/notification-contacts/{contact_key}/test", {
        params: { path: { business_id: business.id, contact_key: contact.key } },
      }),
    { invalidate: [key] },
  );

  const byIdentity = new Map((list.data?.items ?? []).map((contact) => [identity(contact), contact]));

  const sendTest = async (contact: NotificationContact) => {
    setChecking(contact.key);
    const result = await check.run(contact);
    setChecking(null);
    if (!result.ok) {
      return;
    }
    const outcome = contactCheckOutcome(result.data);
    // The contact's name is user content.
    const title = { text: t(outcome.key, { error: result.data.delivery.last_error ?? "" }), values: { name: contact.name } };
    toast.show({ tone: outcome.tone, title });
  };

  return {
    /** The delivery view of a contact of the settings list (undefined while loading or just added). */
    statusOf: (contact: Pick<ManagerContact, "channel" | "address">) => byIdentity.get(identity(contact)),
    checkingKey: checking,
    sendTest,
    reload: list.reload,
  };
}
