"use client";


import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { useToday } from "@/components/insights/useToday";
import type { BookingResult, ConversationSummaryView } from "@/components/insights/types";
import { ErrorState, LoadingRegion, Modal, SkeletonText } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { BookingForm } from "../../bookings/_components/BookingForm";

/**
 * A booking made by staff for the customer of a conversation: the form is
 * filled with the customer, and the booking is linked to the conversation
 * (its channel becomes the source).
 */
export function BookFromConversation({
  open,
  conversation,
  onClose,
  onCreated,
}: {
  open: boolean;
  conversation: ConversationSummaryView;
  onClose: () => void;
  onCreated: (result: BookingResult) => void;
}) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const today = useToday(business.timezone);
  const resources = useQuery(
    queryKeys.resources.list(business.id),
    () => api.GET("/v1/businesses/{business_id}/resources", { params: { path: { business_id: business.id } } }),
    { enabled: open },
  );
  const language =
    conversation.language && business.languages.includes(conversation.language)
      ? conversation.language
      : business.default_language;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={t("conversations.book.title")}
      description={t("conversations.book.description")}
      size="lg"
    >
      {resources.data ? (
        <BookingForm
          resources={resources.data.items ?? []}
          defaultDate={today}
          conversationId={conversation.id}
          initialValues={{
            contactName: conversation.contact_name ?? "",
            phone: conversation.contact_phone_number ?? "",
            source: conversation.channel === "owner_test" ? "phone" : conversation.channel,
            language,
          }}
          onCancel={onClose}
          onCreated={onCreated}
        />
      ) : resources.error ? (
        <ErrorState error={resources.error} onRetry={resources.reload} />
      ) : (
        <LoadingRegion label={t("common.loading")}>
          <SkeletonText lines={6} />
        </LoadingRegion>
      )}
    </Modal>
  );
}
