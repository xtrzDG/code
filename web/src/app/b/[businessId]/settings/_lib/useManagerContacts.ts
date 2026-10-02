"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { api } from "@/api/client";
import type { ApiError } from "@/api/errors";
import { useApiMutation, useApiQuery } from "@/api/hooks";
import { useBusiness } from "@/components/business/BusinessContext";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import {
  applyContactChange,
  contactKey,
  MAX_MANAGER_CONTACTS,
  type ContactChange,
  type ManagerContact,
  type ManagerContactInput,
} from "./contacts";
import type { BusinessView } from "./general";
import { isStaleRevision } from "./revision";

/** The contact being edited (null while adding one); kept by value, as the list may reload under the dialog. */
type Editing = { original: ManagerContact | null } | null;

/**
 * The manager contacts as shown, and saving a change to them. The API
 * saves the whole list with the revision it was made from; refused because
 * someone saved since, the list is reloaded and the open dialog says so.
 */
export function useManagerContacts() {
  const { t } = useI18n();
  const toast = useToast();
  const router = useRouter();
  const { business } = useBusiness();
  const stored = useApiQuery(
    () => api.GET("/v1/businesses/{business_id}", { params: { path: { business_id: business.id } } }),
    [business.id],
  );
  const [saved, setSaved] = useState<BusinessView | null>(null);
  const shown: BusinessView = saved ?? stored.data ?? business;
  const contacts: ManagerContact[] = shown.manager_contacts ?? [];
  const [editing, setEditing] = useState<Editing>(null);
  const [removing, setRemoving] = useState<ManagerContact | null>(null);
  const [dialogError, setDialogError] = useState<ApiError | null>(null);

  const save = useApiMutation(
    (change: ContactChange, base: BusinessView) =>
      api.PATCH("/v1/businesses/{business_id}", {
        params: { path: { business_id: business.id } },
        body: {
          manager_contacts: applyContactChange(base.manager_contacts ?? [], change),
          expected_revision: base.revision,
        },
      }),
    { errorToast: false },
  );
  const isBusy = save.isPending || (saved === null && stored.isLoading);

  const persist = async (change: ContactChange): Promise<boolean> => {
    setDialogError(null);
    const result = await save.run(change, shown);
    if (!result.ok) {
      setDialogError(result.error);
      if (isStaleRevision(result.error)) {
        // Show what is stored now; the dialog stays open for another try.
        setSaved(null);
        stored.reload();
        router.refresh();
      }
      return false;
    }
    setSaved(result.data);
    router.refresh();
    toast.success(t("settings.contacts.saved"));
    return true;
  };

  const onSaveContact = async (contact: ManagerContactInput) => {
    if (!editing) {
      return;
    }
    const change: ContactChange = editing.original
      ? { kind: "edit", original: contactKey(editing.original), contact }
      : { kind: "add", contact };
    if (await persist(change)) {
      setEditing(null);
    }
  };

  const onRemove = async () => {
    if (!removing) {
      return;
    }
    if (await persist({ kind: "remove", original: contactKey(removing) })) {
      setRemoving(null);
    }
  };

  const isFull = contacts.length >= MAX_MANAGER_CONTACTS;

  return {
    contacts,
    isFull,
    isBusy,
    dialogError,
    editing,
    startAdding: () => {
      setDialogError(null);
      setEditing({ original: null });
    },
    startEditing: (contact: ManagerContact) => {
      setDialogError(null);
      setEditing({ original: contact });
    },
    stopEditing: () => setEditing(null),
    onSaveContact,
    removing,
    startRemoving: (contact: ManagerContact) => {
      setDialogError(null);
      setRemoving(contact);
    },
    stopRemoving: () => setRemoving(null),
    onRemove,
  };
}
