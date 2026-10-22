"use client";

/**
 * Passkeys: the person's list (name, when added and last used, synced or
 * not, refused as a copy), adding one with the device's authenticator
 * (the first second factor also answers recovery codes, shown once),
 * renaming and removing. Adding and removing may first ask to confirm it
 * is you (the step-up dialog is global).
 */

import { useState } from "react";

import { api } from "@/api/client";
import { toApiError } from "@/api/errors";
import { unwrap } from "@/api/result";
import type { PasskeyListView, PasskeyView } from "@/api/types";
import { RecoveryCodesPanel } from "@/components/security/RecoveryCodesPanel";
import { Alert, Button, Card, ConfirmDialog, Modal, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { createPasskey, PasskeyCeremonyError } from "@/lib/security/passkeyCeremony";
import { usePasskeySupport } from "@/lib/security/usePasskeySupport";

import { PasskeyRow } from "./PasskeyRow";
import { RenamePasskeyDialog } from "./RenamePasskeyDialog";

export function PasskeysCard({
  initial,
  account,
  onChanged,
}: {
  initial: PasskeyListView;
  account: string;
  onChanged: () => Promise<void>;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const [list, setList] = useState(initial);
  const [isAdding, setAdding] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [codes, setCodes] = useState<string[] | null>(null);
  const [renaming, setRenaming] = useState<PasskeyView | null>(null);
  const [removing, setRemoving] = useState<PasskeyView | null>(null);
  const [isRemoving, setIsRemoving] = useState(false);
  const isSupported = usePasskeySupport();
  const items = list.items ?? [];

  const reload = async () => {
    setList(await unwrap(api.GET("/v1/me/passkeys")));
    await onChanged();
  };

  const add = async () => {
    setAdding(true);
    setProblem(null);
    try {
      const started = await unwrap(api.POST("/v1/me/passkeys/registration"));
      const credential = await createPasskey(started.options);
      const added = await unwrap(
        api.POST("/v1/me/passkeys", {
          body: {
            passkey_challenge_id: started.passkey_challenge_id,
            credential,
          },
        }),
      );
      if (added.recovery_codes && added.recovery_codes.length > 0) {
        // The first second factor: the codes come first, the toast once they are put away.
        setCodes(added.recovery_codes);
      } else {
        toast.success(t("passkeys.added"));
      }
      await reload();
    } catch (caught) {
      if (caught instanceof PasskeyCeremonyError) {
        setProblem(t(caught.messageKey));
      } else {
        toast.error(toApiError(caught));
      }
    } finally {
      setAdding(false);
    }
  };

  const closeCodes = () => {
    setCodes(null);
    toast.success(t("passkeys.added"));
  };

  const remove = async () => {
    if (!removing) {
      return;
    }
    setIsRemoving(true);
    try {
      await unwrap(
        api.DELETE("/v1/me/passkeys/{passkey_id}", {
          params: { path: { passkey_id: removing.id } },
        }),
      );
      setRemoving(null);
      toast.success(t("passkeys.removed"));
      await reload();
    } catch (error) {
      toast.error(toApiError(error));
    } finally {
      setIsRemoving(false);
    }
  };

  return (
    <Card title={t("passkeys.title")} description={t("passkeys.description")}>
      <div className="space-y-4">
        {!list.is_available ? (
          <p className="text-sm text-ink-muted">{t("passkeys.unavailable")}</p>
        ) : isSupported === false ? (
          <p className="text-sm text-ink-muted">{t("passkeys.unsupported")}</p>
        ) : list.is_recommended || items.length === 0 ? (
          <p className="text-sm text-ink-muted">{t("passkeys.recommended")}</p>
        ) : null}
        {items.length > 0 ? (
          <ul className="divide-y divide-line" aria-label={t("passkeys.title")}>
            {items.map((passkey) => (
              <PasskeyRow
                key={passkey.id}
                passkey={passkey}
                onRename={setRenaming}
                onRemove={setRemoving}
              />
            ))}
          </ul>
        ) : list.is_available ? (
          <p className="text-sm text-ink-subtle">{t("passkeys.empty")}</p>
        ) : null}
        {problem ? <Alert tone="warning">{problem}</Alert> : null}
        {list.is_available && isSupported === true ? (
          <Button
            isLoading={isAdding}
            loadingText={t("passkeys.adding")}
            onClick={() => void add()}
          >
            {t("passkeys.add")}
          </Button>
        ) : null}
      </div>

      <RenamePasskeyDialog
        passkey={renaming}
        onClose={() => setRenaming(null)}
        onRenamed={async () => {
          setRenaming(null);
          toast.success(t("passkeys.renamed"));
          await reload();
        }}
      />

      <Modal
        open={codes !== null}
        onClose={closeCodes}
        title={t("mfa.recovery.title")}
      >
        {codes ? (
          <RecoveryCodesPanel
            codes={codes}
            account={account}
            onDone={closeCodes}
            doneLabel={t("common.done")}
          />
        ) : null}
      </Modal>

      <ConfirmDialog
        open={removing !== null}
        onClose={() => setRemoving(null)}
        onConfirm={remove}
        isPending={isRemoving}
        title={t("passkeys.removeTitle")}
        confirmLabel={t("passkeys.remove")}
      >
        <p>{t("passkeys.removeDescription")}</p>
      </ConfirmDialog>
    </Card>
  );
}
