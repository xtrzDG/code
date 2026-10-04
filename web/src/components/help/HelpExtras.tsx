"use client";

/**
 * The end of a help page: how to reach support and, for someone signed in,
 * bringing back the tips they closed.
 */

import { Button, Card } from "@/components/ui";
import { useToast } from "@/components/ui/Toast";
import { useI18n } from "@/i18n/client";

import { SupportContacts } from "./SupportContacts";
import { useHelpProgress } from "./useHelp";

const ROW =
  "flex min-h-11 w-full items-center gap-3 rounded-lg px-2.5 text-sm text-ink-muted transition-colors hover:bg-surface-muted hover:text-ink";

export function HelpExtras({ signedIn }: { signedIn: boolean }) {
  const { t } = useI18n();
  return (
    <Card title={t("helpCenter.stillStuck")} description={t("helpCenter.stillStuckLead")}>
      <div className="space-y-4">
        <SupportContacts rowClassName={ROW} />
        {signedIn ? <TipsAgain /> : null}
      </div>
    </Card>
  );
}

function TipsAgain() {
  const { t } = useI18n();
  const toast = useToast();
  const { resetTips, isResetting } = useHelpProgress(false);
  return (
    <Button
      variant="secondary"
      size="sm"
      isLoading={isResetting}
      onClick={async () => {
        if (await resetTips()) {
          toast.success(t("helpCenter.tipsShown"));
        }
      }}
    >
      {t("helpCenter.tipsAgain")}
    </Button>
  );
}
