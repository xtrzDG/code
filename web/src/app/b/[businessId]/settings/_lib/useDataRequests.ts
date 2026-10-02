"use client";

import { useEffect, useState } from "react";

import { api } from "@/api/client";
import type { ApiError } from "@/api/errors";
import { queryKeys } from "@/api/queryKeys";
import { unwrap } from "@/api/result";
import { useCursorPage } from "@/api/useCursorPage";
import { useMutation } from "@/api/useMutation";
import { useBusiness } from "@/components/business/BusinessContext";
import { useToast } from "@/components/ui";
import { downloadJson, isoDay } from "@/components/workspace/helpers";
import { useI18n } from "@/i18n/client";

import {
  CONTACTS_PAGE_SIZE,
  contactSearchParam,
  markErased,
  type ContactPage,
  type ContactSummary,
} from "./customers";

const SEARCH_DELAY_MS = 300;

/**
 * Customers' data requests: the customer list (searched as the owner
 * types), exporting one customer's data and erasing it.
 */
export function useDataRequests() {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState<string | undefined>(undefined);
  const [exporting, setExporting] = useState<string | null>(null);
  const [erasing, setErasing] = useState<ContactSummary | null>(null);
  const [erasureError, setErasureError] = useState<ApiError | null>(null);
  // Whose data was erased last (the API answers 204), for the summary.
  const [lastErasedName, setLastErasedName] = useState<string | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => setSearch(contactSearchParam(query)), SEARCH_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [query]);

  const contacts = useCursorPage<ContactSummary, ContactPage>(
    queryKeys.settings.contacts(business.id, search ?? null),
    ({ cursor, limit }) =>
      api.GET("/v1/businesses/{business_id}/contacts", {
        params: {
          path: { business_id: business.id },
          query: { search, limit: String(limit), ...(cursor ? { cursor } : {}) },
        },
      }),
    { pageSize: CONTACTS_PAGE_SIZE },
  );
  const erase = useMutation(
    (contactId: string) =>
      api.DELETE("/v1/businesses/{business_id}/contacts/{contact_id}", {
        params: { path: { business_id: business.id, contact_id: contactId } },
      }),
    {
      errorToast: false,
      // The customer's name and phone go from every list that showed them.
      stale: [
        queryKeys.conversations.all(business.id),
        queryKeys.bookings.all(business.id),
        queryKeys.leads.all(business.id),
        queryKeys.handoffs.all(business.id),
        queryKeys.inbox.all(business.id),
      ],
    },
  );

  const displayName = (contact: ContactSummary) => contact.name || contact.phone_number || t("settings.requests.unnamed");

  const onExport = async (contact: ContactSummary) => {
    setExporting(contact.id);
    try {
      const data = await unwrap(
        api.GET("/v1/businesses/{business_id}/contacts/{contact_id}/export", {
          params: { path: { business_id: business.id, contact_id: contact.id } },
        }),
      );
      downloadJson(data, `${contact.id}-${isoDay(new Date())}.json`);
      toast.success(t("settings.requests.exported"));
    } catch (error) {
      toast.error(error);
    } finally {
      setExporting(null);
    }
  };

  const onErase = async () => {
    if (!erasing) {
      return;
    }
    const result = await erase.run(erasing.id);
    if (!result.ok) {
      setErasureError(result.error);
      return;
    }
    const erasedId = erasing.id;
    const erasedAt = Date.now() * 1000;
    setErasing(null);
    setLastErasedName(displayName(erasing));
    contacts.updateItems((items) => items.map((item) => (item.id === erasedId ? markErased(item, erasedAt) : item)));
    toast.success(t("settings.requests.deleted"));
  };

  return {
    query,
    setQuery,
    search,
    contacts,
    exporting,
    erasing,
    startErasing: (contact: ContactSummary) => {
      setErasureError(null);
      setErasing(contact);
    },
    stopErasing: () => setErasing(null),
    erasureError,
    isErasing: erase.isPending,
    lastErasedName,
    displayName,
    onExport,
    onErase,
  };
}
