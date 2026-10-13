import { getI18n } from "@/i18n/server";

import { ConversationDetailSkeleton } from "./_components/conversation/ConversationDetailSkeleton";
import { ConversationHeaderPreview } from "./_components/conversation/ConversationHeaderPreview";

/**
 * A conversation on its way (the list beside it stays: it lives in the
 * layout), with its header from the list at once: the row's customer
 * flies into it.
 */
export default async function ConversationLoading() {
  const { t } = await getI18n();
  return <ConversationDetailSkeleton label={t("conversations.loadingOne")} header={<ConversationHeaderPreview />} />;
}
