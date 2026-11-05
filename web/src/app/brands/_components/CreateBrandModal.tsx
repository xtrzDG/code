"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import type { UserMembershipView } from "@/api/types";
import { Button, Field, Input, Modal, ModalFooter, Select, useToast } from "@/components/ui";
import { InlineError } from "@/components/ui/InlineError";
import { useI18n } from "@/i18n/client";
import { brandPath } from "@/lib/navigation";

import { useCreateBrand } from "../_lib/useBrands";

/** A new brand: its name and its first location, a business the person owns. */
export function CreateBrandModal({
  open,
  onClose,
  candidates,
}: {
  open: boolean;
  onClose: () => void;
  candidates: readonly UserMembershipView[];
}) {
  const { t } = useI18n();
  return (
    <Modal open={open} onClose={onClose} title={t("brands.create.title")} description={t("brands.create.description")}>
      {open ? <CreateBrandForm onClose={onClose} candidates={candidates} /> : null}
    </Modal>
  );
}

function CreateBrandForm({ onClose, candidates }: { onClose: () => void; candidates: readonly UserMembershipView[] }) {
  const { t } = useI18n();
  const toast = useToast();
  const router = useRouter();
  const create = useCreateBrand();
  const [name, setName] = useState("");
  const [businessId, setBusinessId] = useState(candidates[0]?.business_id ?? "");
  const [nameError, setNameError] = useState(false);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = name.trim();
    if (trimmed === "") {
      setNameError(true);
      return;
    }
    const result = await create.run(trimmed, businessId);
    if (result.ok) {
      toast.success({ text: t("brands.create.created"), values: { name: result.data.name } });
      onClose();
      router.push(brandPath(result.data.id));
      router.refresh();
    }
  };

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-5">
      <Field label={t("brands.create.name")} required error={nameError ? t("brands.create.errors.name") : undefined}>
        {(control) => (
          <Input
            {...control}
            value={name}
            dir="auto"
            maxLength={100}
            autoComplete="off"
            placeholder={t("brands.create.namePlaceholder")}
            onChange={(event) => {
              setName(event.target.value);
              setNameError(false);
            }}
          />
        )}
      </Field>
      <Field label={t("brands.create.firstLocation")} required>
        {(control) => (
          <Select {...control} value={businessId} onChange={(event) => setBusinessId(event.target.value)}>
            {candidates.map((candidate) => (
              <option key={candidate.business_id} value={candidate.business_id}>
                {candidate.business_name}
              </option>
            ))}
          </Select>
        )}
      </Field>
      <InlineError error={create.error} overrides={{ conflict: "brands.create.errors.inBrand" }} />
      <ModalFooter>
        <Button variant="secondary" onClick={onClose} disabled={create.isPending}>
          {t("common.cancel")}
        </Button>
        <Button type="submit" isLoading={create.isPending}>
          {t("brands.create.submit")}
        </Button>
      </ModalFooter>
    </form>
  );
}
