"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import type { UserMembershipView } from "@/api/types";
import { Alert, Button, Field, Input, Modal, ModalFooter, Select, useToast } from "@/components/ui";
import { InlineError } from "@/components/ui/InlineError";
import { useI18n } from "@/i18n/client";

import type { BrandLocationView } from "../_lib/brands";
import { useBrandSettings } from "../_lib/useBrands";

/** One of the owner's businesses, in no brand yet, joins this one. */
export function AddLocationModal({
  open,
  onClose,
  brandId,
  candidates,
}: {
  open: boolean;
  onClose: () => void;
  brandId: string;
  candidates: readonly UserMembershipView[];
}) {
  const { t } = useI18n();
  return (
    <Modal open={open} onClose={onClose} title={t("brands.locations.addTitle")} description={t("brands.locations.addDescription")}>
      {open ? <AddForm onClose={onClose} brandId={brandId} candidates={candidates} /> : null}
    </Modal>
  );
}

function AddForm({ onClose, brandId, candidates }: { onClose: () => void; brandId: string; candidates: readonly UserMembershipView[] }) {
  const { t } = useI18n();
  const toast = useToast();
  const router = useRouter();
  const { addLocation } = useBrandSettings(brandId);
  const [businessId, setBusinessId] = useState(candidates[0]?.business_id ?? "");

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const chosen = candidates.find((candidate) => candidate.business_id === businessId);
    if (!chosen) {
      return;
    }
    const result = await addLocation.run(chosen.business_id);
    if (result.ok) {
      toast.success({ text: t("brands.locations.added"), values: { name: chosen.business_name } });
      onClose();
      router.refresh();
    }
  };

  if (candidates.length === 0) {
    return (
      <>
        <p className="text-sm text-ink-muted">{t("brands.locations.noCandidates")}</p>
        <ModalFooter>
          <Button variant="secondary" onClick={onClose}>
            {t("common.close")}
          </Button>
        </ModalFooter>
      </>
    );
  }
  return (
    <form onSubmit={onSubmit} noValidate className="space-y-5">
      <Field label={t("brands.locations.pick")} required>
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
      <InlineError error={addLocation.error} overrides={{ conflict: "brands.create.errors.inBrand" }} />
      <ModalFooter>
        <Button variant="secondary" onClick={onClose} disabled={addLocation.isPending}>
          {t("common.cancel")}
        </Button>
        <Button type="submit" isLoading={addLocation.isPending}>
          {t("brands.locations.add")}
        </Button>
      </ModalFooter>
    </form>
  );
}

/** "New location from…": a copy of one location, never its tokens, payments, keys, webhooks or customers. */
export function CloneLocationModal({
  open,
  onClose,
  brandId,
  locations,
}: {
  open: boolean;
  onClose: () => void;
  brandId: string;
  locations: readonly BrandLocationView[];
}) {
  const { t } = useI18n();
  return (
    <Modal open={open} onClose={onClose} title={t("brands.locations.cloneTitle")} description={t("brands.locations.cloneDescription")}>
      {open ? <CloneForm onClose={onClose} brandId={brandId} locations={locations} /> : null}
    </Modal>
  );
}

function CloneForm({ onClose, brandId, locations }: { onClose: () => void; brandId: string; locations: readonly BrandLocationView[] }) {
  const { t } = useI18n();
  const toast = useToast();
  const router = useRouter();
  const { cloneLocation } = useBrandSettings(brandId);
  const [sourceId, setSourceId] = useState(locations[0]?.business_id ?? "");
  const [name, setName] = useState("");
  const [city, setCity] = useState("");
  const [isBlank, setBlank] = useState(false);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (name.trim() === "") {
      setBlank(true);
      return;
    }
    const result = await cloneLocation.run({ source_business_id: sourceId, name: name.trim(), city: city.trim() || null });
    if (result.ok) {
      toast.success({ text: t("brands.locations.cloned"), values: { name: result.data.name } });
      onClose();
      router.refresh();
    }
  };

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-5">
      <Field label={t("brands.locations.source")} required>
        {(control) => (
          <Select {...control} value={sourceId} onChange={(event) => setSourceId(event.target.value)}>
            {locations.map((location) => (
              <option key={location.business_id} value={location.business_id}>
                {location.name}
              </option>
            ))}
          </Select>
        )}
      </Field>
      <Field label={t("brands.locations.name")} required error={isBlank ? t("brands.locations.errors.name") : undefined}>
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
      <Field label={t("brands.locations.city")} optionalLabel={t("common.optional")}>
        {(control) => <Input {...control} value={city} dir="auto" maxLength={100} autoComplete="off" onChange={(event) => setCity(event.target.value)} />}
      </Field>
      <Alert tone="info">{t("brands.locations.cloneNever")}</Alert>
      <InlineError error={cloneLocation.error} />
      <ModalFooter>
        <Button variant="secondary" onClick={onClose} disabled={cloneLocation.isPending}>
          {t("common.cancel")}
        </Button>
        <Button type="submit" isLoading={cloneLocation.isPending}>
          {t("brands.locations.cloneSubmit")}
        </Button>
      </ModalFooter>
    </form>
  );
}
