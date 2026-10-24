"use client";

import { useState, type FormEvent } from "react";

import { Button, Modal, ModalFooter, UserSentence, useToast } from "@/components/ui";
import { InlineError } from "@/components/ui/InlineError";
import { useI18n } from "@/i18n/client";

import { brandMemberLabel, type BrandLocationView, type BrandMemberRole, type BrandMemberView } from "../_lib/brands";
import { useBrandTeam } from "../_lib/useBrands";
import { RoleFields } from "./RoleFields";

/** A member's new role, and the locations a regional manager runs. */
export function MemberRoleModal({
  member,
  onClose,
  brandId,
  locations,
}: {
  member: BrandMemberView | null;
  onClose: () => void;
  brandId: string;
  locations: readonly BrandLocationView[];
}) {
  const { t } = useI18n();
  return (
    <Modal
      open={member !== null}
      onClose={onClose}
      title={member ? <UserSentence text={t("brands.team.editTitle")} values={{ name: brandMemberLabel(member) }} /> : ""}
    >
      {member ? <RoleForm key={member.user_id} member={member} onClose={onClose} brandId={brandId} locations={locations} /> : null}
    </Modal>
  );
}

function RoleForm({
  member,
  onClose,
  brandId,
  locations,
}: {
  member: BrandMemberView;
  onClose: () => void;
  brandId: string;
  locations: readonly BrandLocationView[];
}) {
  const { t } = useI18n();
  const toast = useToast();
  const { change } = useBrandTeam(brandId);
  const [role, setRole] = useState<BrandMemberRole>(member.role);
  const [businessIds, setBusinessIds] = useState<string[]>([...(member.business_ids ?? [])]);
  const [isMissingLocations, setMissingLocations] = useState(false);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (role === "regional_manager" && businessIds.length === 0) {
      setMissingLocations(true);
      return;
    }
    const result = await change.run(member.user_id, { role, business_ids: role === "regional_manager" ? businessIds : [] });
    if (result.ok) {
      toast.success({ text: t("brands.team.changed"), values: { name: brandMemberLabel(member) } });
      onClose();
    }
  };

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-5">
      <RoleFields
        idPrefix={`brand-member-${member.user_id}`}
        role={role}
        businessIds={businessIds}
        locations={locations}
        locationsError={isMissingLocations ? t("brands.team.errors.locations") : undefined}
        onChange={(next) => {
          if (next.role) setRole(next.role);
          if (next.businessIds) setBusinessIds(next.businessIds);
          setMissingLocations(false);
        }}
      />
      <InlineError error={change.error} overrides={{ conflict: "brands.team.errors.lastOwner" }} />
      <ModalFooter>
        <Button variant="secondary" onClick={onClose} disabled={change.isPending}>
          {t("common.cancel")}
        </Button>
        <Button type="submit" isLoading={change.isPending}>
          {t("brands.team.save")}
        </Button>
      </ModalFooter>
    </form>
  );
}
