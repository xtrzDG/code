"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button, ConfirmDialog, Field, Input, Modal, ModalFooter, UserSentence, useToast } from "@/components/ui";
import { InlineError } from "@/components/ui/InlineError";
import { useI18n } from "@/i18n/client";
import { BRANDS_PATH } from "@/lib/navigation";

import type { BrandView } from "../_lib/brands";
import { useBrandSettings } from "../_lib/useBrands";

/** A brand's new name (brand owners). */
export function RenameBrandModal({ brand, open, onClose }: { brand: BrandView; open: boolean; onClose: () => void }) {
  const { t } = useI18n();
  return (
    <Modal open={open} onClose={onClose} title={t("brands.manage.renameTitle")}>
      {open ? <RenameForm brand={brand} onClose={onClose} /> : null}
    </Modal>
  );
}

function RenameForm({ brand, onClose }: { brand: BrandView; onClose: () => void }) {
  const { t } = useI18n();
  const toast = useToast();
  const router = useRouter();
  const { rename } = useBrandSettings(brand.id);
  const [name, setName] = useState(brand.name);
  const [isBlank, setBlank] = useState(false);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (name.trim() === "") {
      setBlank(true);
      return;
    }
    const result = await rename.run(name.trim());
    if (result.ok) {
      toast.success(t("brands.manage.renamed"));
      onClose();
      router.refresh();
    }
  };

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-5">
      <Field label={t("brands.create.name")} required error={isBlank ? t("brands.create.errors.name") : undefined}>
        {(control) => (
          <Input
            {...control}
            value={name}
            dir="auto"
            maxLength={100}
            autoComplete="off"
            onChange={(event) => {
              setName(event.target.value);
              setBlank(false);
            }}
          />
        )}
      </Field>
      <InlineError error={rename.error} />
      <ModalFooter>
        <Button variant="secondary" onClick={onClose} disabled={rename.isPending}>
          {t("common.cancel")}
        </Button>
        <Button type="submit" isLoading={rename.isPending}>
          {t("common.save")}
        </Button>
      </ModalFooter>
    </form>
  );
}

/** Deleting a brand: only once every location is out of it (the API refuses otherwise). */
export function DeleteBrandDialog({ brand, open, onClose }: { brand: BrandView; open: boolean; onClose: () => void }) {
  const { t } = useI18n();
  const toast = useToast();
  const router = useRouter();
  const { remove } = useBrandSettings(brand.id);
  const hasLocations = (brand.locations ?? []).length > 0;

  const onConfirm = async () => {
    const result = await remove.run();
    if (result.ok) {
      toast.success({ text: t("brands.manage.deleted"), values: { name: brand.name } });
      onClose();
      router.push(BRANDS_PATH);
      router.refresh();
    }
  };

  return (
    <ConfirmDialog
      open={open}
      onClose={onClose}
      onConfirm={onConfirm}
      title={<UserSentence text={t("brands.manage.deleteTitle")} values={{ name: brand.name }} />}
      description={hasLocations ? t("brands.manage.deleteBlocked") : t("brands.manage.deleteDescription")}
      confirmLabel={t("brands.manage.deleteBrand")}
      confirmDisabled={hasLocations}
      isPending={remove.isPending}
      error={remove.error}
      errorOverrides={{ conflict: "brands.manage.deleteBlocked" }}
    />
  );
}
