"use client";

/** The name a person gives a passkey, to tell it apart in their list. */

import { useState } from "react";

import { api } from "@/api/client";
import { toApiError } from "@/api/errors";
import { unwrap } from "@/api/result";
import type { PasskeyView } from "@/api/types";
import { Button, Field, Input, Modal, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

const MAX_NAME_LENGTH = 60;

export function RenamePasskeyDialog({
  passkey,
  onClose,
  onRenamed,
}: {
  passkey: PasskeyView | null;
  onClose: () => void;
  onRenamed: () => Promise<void>;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const [name, setName] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [isSaving, setSaving] = useState(false);

  if (passkey && passkey.id !== editingId) {
    setEditingId(passkey.id);
    setName(passkey.name);
  }

  const trimmed = name.trim();

  const save = async () => {
    if (!passkey || trimmed === "") {
      return;
    }
    setSaving(true);
    try {
      await unwrap(
        api.PATCH("/v1/me/passkeys/{passkey_id}", {
          params: { path: { passkey_id: passkey.id } },
          body: { name: trimmed },
        }),
      );
      await onRenamed();
    } catch (error) {
      toast.error(toApiError(error));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open={passkey !== null}
      onClose={onClose}
      title={t("passkeys.renameTitle")}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button
            isLoading={isSaving}
            disabled={trimmed === ""}
            onClick={() => void save()}
          >
            {t("passkeys.save")}
          </Button>
        </>
      }
    >
      <form
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <Field label={t("passkeys.name")} hint={t("passkeys.renameHint")}>
          {(control) => (
            <Input
              {...control}
              value={name}
              maxLength={MAX_NAME_LENGTH}
              autoComplete="off"
              autoFocus
              onChange={(event) => setName(event.target.value)}
            />
          )}
        </Field>
      </form>
    </Modal>
  );
}
