"use client";

/**
 * Who receives what the assistant cannot answer: the business's staff
 * contacts, adding the owner (one tap) or someone else, removing one, and
 * linking a Telegram chat through the platform's bot (the link is opened on
 * a phone; the business is read again every few seconds until the chat
 * appears).
 */

import { useEffect, useState } from "react";

import { api } from "@/api/client";
import type { ApiError } from "@/api/errors";
import { unwrap } from "@/api/result";
import type { Schema } from "@/api/types";
import { applyContactChange, type ContactChange, type ManagerContactInput } from "@/app/b/[businessId]/settings/_lib/contacts";
import { useBusiness } from "@/components/business/BusinessContext";
import { hasNewTelegramContact } from "@/lib/tunnel/contacts";

import { useSaveTracker } from "../SaveTracker";
import { useBusinessSave } from "../flow/useBusinessSave";

const LINK_POLL_MS = 3_000;

type TelegramLink = Schema<"TelegramLinkView">;

export function usePeople(businessId: string) {
  const { business: initial } = useBusiness();
  const track = useSaveTracker();
  const stored = useBusinessSave(businessId);
  const business = stored.business ?? initial;
  const contacts = business.manager_contacts ?? [];
  const [isSaving, setSaving] = useState(false);
  const [link, setLink] = useState<{ link: TelegramLink; before: Schema<"ManagerContactView">[] } | null>(null);
  const [linkError, setLinkError] = useState<ApiError | null>(null);
  const [isLinking, setLinking] = useState(false);

  const change = async (contactChange: ContactChange): Promise<boolean> => {
    setSaving(true);
    const saved = await track(
      stored.save((current) => ({ manager_contacts: applyContactChange(current.manager_contacts ?? [], contactChange) })).then((result) => result !== null),
    );
    setSaving(false);
    return saved;
  };

  const add = (contact: ManagerContactInput) => change({ kind: "add", contact });
  const remove = (contact: Schema<"ManagerContactView">) => change({ kind: "remove", original: { channel: contact.channel, address: contact.address } });

  const startTelegram = async (name: string) => {
    setLinking(true);
    setLinkError(null);
    try {
      const created = await unwrap(
        api.POST("/v1/businesses/{business_id}/manager-contacts/telegram-link", {
          params: { path: { business_id: businessId } },
          body: { name, language: business.owner_language },
        }),
      );
      setLink({ link: created, before: contacts });
    } catch (error) {
      setLinkError(error as ApiError);
    } finally {
      setLinking(false);
    }
  };

  const isLinked = link !== null && hasNewTelegramContact(link.before, contacts);
  const reloadBusiness = stored.reload;

  // While a link waits to be opened, look for the new chat every few seconds.
  useEffect(() => {
    if (!link || isLinked) {
      return;
    }
    const timer = setInterval(reloadBusiness, LINK_POLL_MS);
    return () => clearInterval(timer);
  }, [link, isLinked, reloadBusiness]);

  return {
    contacts,
    isLoading: stored.isLoading,
    isSaving,
    add,
    remove,
    telegram: { link: link?.link ?? null, isLinked, isLinking, error: linkError, start: startTelegram, cancel: () => setLink(null) },
  };
}
