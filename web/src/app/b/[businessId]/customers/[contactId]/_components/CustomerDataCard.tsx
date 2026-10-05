"use client";

/**
 * A customer's data requests (owners; moved here from Settings → Privacy):
 * export everything about them as a JSON file, or erase it for good after
 * typing their name. Both are audited by the API.
 */

import { useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { unwrap } from "@/api/result";
import { useMutation } from "@/api/useMutation";
import type { Query } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconDownload, IconShield } from "@/components/icons";
import { Button, Card, ConfirmDialog, useToast } from "@/components/ui";
import { downloadJson, isoDay } from "@/components/workspace/helpers";
import { useI18n } from "@/i18n/client";

import { erasureConfirmation, markErased, type CustomerDetail } from "../../_lib/customerModel";

export function CustomerDataCard({ detail, name }: { detail: Query<CustomerDetail>; name: string }) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const [isExporting, setExporting] = useState(false);
  const [isErasing, setErasing] = useState(false);
  const data = detail.data;
  const contactId = data?.contact.id ?? "";

  const erase = useMutation(
    () =>
      api.DELETE("/v1/businesses/{business_id}/contacts/{contact_id}", {
        params: { path: { business_id: business.id, contact_id: contactId } },
      }),
    {
      errorToast: false,
      // The customer's name and phone go from every list that showed them.
      stale: [
        queryKeys.customers.all(business.id),
        queryKeys.conversations.all(business.id),
        queryKeys.bookings.all(business.id),
        queryKeys.leads.all(business.id),
        queryKeys.handoffs.all(business.id),
        queryKeys.inbox.all(business.id),
      ],
    },
  );

  if (!data || data.contact.erased_at) {
    return null;
  }

  const onExport = async () => {
    setExporting(true);
    try {
      const exported = await unwrap(
        api.GET("/v1/businesses/{business_id}/contacts/{contact_id}/export", {
          params: { path: { business_id: business.id, contact_id: contactId } },
        }),
      );
      downloadJson(exported, `${contactId}-${isoDay(new Date())}.json`);
      toast.success(t("settings.requests.exported"));
    } catch (error) {
      toast.error(error);
    } finally {
      setExporting(false);
    }
  };

  const onErase = async () => {
    const result = await erase.run();
    if (!result.ok) {
      return;
    }
    const erasedAt = Date.now() * 1000;
    detail.setData((current) =>
      current ? { ...current, blocked_at: null, contact: markErased(current.contact, erasedAt) } : current,
    );
    setErasing(false);
    toast.success(t("settings.requests.deletedSummary", { name }));
  };

  return (
    <Card title={t("customers.data.title")} description={t("customers.data.description")}>
      <div className="flex flex-wrap gap-2">
        <Button
          variant="secondary"
          leadingIcon={<IconDownload className="size-4" aria-hidden />}
          isLoading={isExporting}
          aria-label={t("settings.requests.exportLabel", { name })}
          onClick={() => void onExport()}
        >
          {t("settings.requests.export")}
        </Button>
        <Button variant="danger-ghost" aria-label={t("settings.requests.deleteLabel", { name })} onClick={() => setErasing(true)}>
          {t("settings.requests.delete")}
        </Button>
      </div>
      <ConfirmDialog
        open={isErasing}
        onClose={() => setErasing(false)}
        onConfirm={onErase}
        isPending={erase.isPending}
        error={erase.error}
        title={t("settings.requests.deleteTitle", { name })}
        confirmLabel={t("settings.requests.deleteConfirm")}
        confirmationText={erasureConfirmation(data.contact)}
      >
        <p className="flex gap-2">
          <IconShield className="mt-0.5 size-4 shrink-0 text-danger" aria-hidden />
          <span>{t("settings.requests.deleteDescription")}</span>
        </p>
      </ConfirmDialog>
    </Card>
  );
}
