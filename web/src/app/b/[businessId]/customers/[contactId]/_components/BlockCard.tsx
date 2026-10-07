"use client";

/**
 * Owners block a customer for spam or abuse: the assistant stops answering
 * them in every channel and nothing is sent to them, while their messages
 * still reach the inbox. Blocking asks first; unblocking does not.
 */

import { useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import type { Query } from "@/api/useQuery";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconShield } from "@/components/icons";
import { Alert, Button, Card, ConfirmDialog, UserSentence, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { namingSentence, withCard, type CustomerDetail, type CustomerNaming } from "../../_lib/customerModel";

export function BlockCard({ detail, naming }: { detail: Query<CustomerDetail>; naming: CustomerNaming }) {
  const { t } = useI18n();
  const toast = useToast();
  const format = useBusinessFormat();
  const { business } = useBusiness();
  const [isAsking, setAsking] = useState(false);
  const data = detail.data;
  const contactId = data?.contact.id ?? "";

  const setBlocked = useMutation(
    (isBlocked: boolean) =>
      api.PUT("/v1/businesses/{business_id}/contacts/{contact_id}/blocking", {
        params: { path: { business_id: business.id, contact_id: contactId } },
        body: { is_blocked: isBlocked },
      }),
    { errorToast: false, stale: [queryKeys.customers.all(business.id), queryKeys.inbox.all(business.id)] },
  );

  if (!data || data.contact.erased_at) {
    return null;
  }
  const isBlocked = data.contact.is_blocked ?? false;

  const change = async (block: boolean) => {
    const result = await setBlocked.run(block);
    if (!result.ok) {
      if (!block) {
        toast.error(result.error);
      }
      return;
    }
    detail.setData((current) => (current ? withCard(current, result.data) : current));
    setAsking(false);
    toast.success(namingSentence(t(block ? "customers.block.blocked" : "customers.block.unblocked"), naming));
  };

  return (
    <Card title={t("customers.block.title")} description={t("customers.block.description")}>
      {isBlocked ? (
        <div className="space-y-3">
          <Alert tone="warning">
            {t("customers.detail.blockedSince", { date: data.blocked_at ? format.dateTime(data.blocked_at) : "—" })}
          </Alert>
          <Button variant="secondary" isLoading={setBlocked.isPending} onClick={() => void change(false)}>
            {t("customers.block.unblock")}
          </Button>
        </div>
      ) : (
        <Button
          variant="danger-ghost"
          leadingIcon={<IconShield className="size-4" aria-hidden />}
          onClick={() => setAsking(true)}
        >
          {t("customers.block.action")}
        </Button>
      )}
      <ConfirmDialog
        open={isAsking}
        onClose={() => setAsking(false)}
        onConfirm={() => change(true)}
        isPending={setBlocked.isPending}
        error={setBlocked.error}
        title={<UserSentence {...namingSentence(t("customers.block.confirmTitle"), naming)} />}
        confirmLabel={t("customers.block.confirm")}
      >
        <p>{t("customers.block.confirmBody")}</p>
      </ConfirmDialog>
    </Card>
  );
}
