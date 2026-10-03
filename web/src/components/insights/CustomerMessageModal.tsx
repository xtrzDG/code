"use client";

import { IconClipboard } from "@/components/icons";
import { Button, Modal, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

/**
 * The text the API prepared for the customer (booking confirmation, new
 * time, cancellation) with a copy button: bookings made in the cabinet are
 * not sent to the customer by the assistant.
 */
export function CustomerMessageModal({
  open,
  title,
  text,
  onClose,
}: {
  open: boolean;
  /** What happened ("Booking created"). */
  title: string;
  text: string;
  onClose: () => void;
}) {
  const { t } = useI18n();
  const toast = useToast();

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success(t("insights.copied"));
    } catch {
      toast.info(t("insights.copyFailed"));
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      description={t("insights.customerMessage.description")}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t("common.done")}
          </Button>
          <Button leadingIcon={<IconClipboard className="size-4" aria-hidden />} onClick={copy}>
            {t("insights.copy")}
          </Button>
        </>
      }
    >
      <p className="mb-2 text-sm font-medium text-ink">{t("insights.customerMessage.title")}</p>
      <p
        dir="auto"
        className="rounded-xl border border-line bg-surface-muted px-4 py-3 text-sm whitespace-pre-wrap text-ink select-all"
      >
        {text}
      </p>
    </Modal>
  );
}
