"use client";

import { useState } from "react";

import { IconKey, IconRefresh } from "@/components/icons";
import { Alert, Badge, Button, Card, ConfirmDialog, EmptyState } from "@/components/ui";
import { useViewerFormat } from "@/components/time/ViewerTimeZone";
import { Facts } from "@/components/workspace/Facts";
import { useToast } from "@/components/ui/Toast";
import { useI18n } from "@/i18n/client";
import { formatNumber } from "@/lib/format";

import {
  ROTATION_STATUS_TONES,
  findingTone,
  rotationFindings,
  type KeyRotation,
  type RotationFinding,
} from "../../_lib/keyRotation";

interface RotationCardProps {
  latest: KeyRotation | null;
  keyCount: number;
  isRunning: boolean;
  isStarting: boolean;
  startError: unknown;
  onStart: () => Promise<boolean>;
}

/** The latest re-encryption run (its counts and what they mean) and the start of a new one. */
export function RotationCard({ latest, keyCount, isRunning, isStarting, startError, onStart }: RotationCardProps) {
  const { t } = useI18n();
  const toast = useToast();
  const [isConfirming, setConfirming] = useState(false);

  const confirm = async () => {
    if (await onStart()) {
      setConfirming(false);
      toast.success(t("adminSecurity.run.started"));
    }
  };

  return (
    <Card
      aria-label={t("adminSecurity.run.title")}
      title={t("adminSecurity.run.title")}
      description={t("adminSecurity.run.description")}
      actions={
        <Button
          leadingIcon={<IconRefresh className="size-4" aria-hidden />}
          onClick={() => setConfirming(true)}
          disabled={isRunning}
        >
          {t("adminSecurity.run.start")}
        </Button>
      }
    >
      {latest === null ? (
        <EmptyState
          icon={<IconKey className="size-6" />}
          title={t("adminSecurity.run.none")}
          description={t("adminSecurity.run.noneDescription")}
        />
      ) : (
        <div className="space-y-5" aria-live="polite">
          <RunFindings rotation={latest} keyCount={keyCount} />
          <RunFacts rotation={latest} />
        </div>
      )}

      <ConfirmDialog
        open={isConfirming}
        onClose={() => setConfirming(false)}
        onConfirm={confirm}
        tone="primary"
        title={t("adminSecurity.run.confirmTitle")}
        description={t("adminSecurity.run.confirmBody")}
        confirmLabel={t("adminSecurity.run.confirm")}
        pendingLabel={t("adminSecurity.run.starting")}
        isPending={isStarting}
        error={startError}
        errorOverrides={{ conflict: "adminSecurity.run.alreadyRunning" }}
      />
    </Card>
  );
}

function RunFindings({ rotation, keyCount }: { rotation: KeyRotation; keyCount: number }) {
  return (
    <div className="space-y-3">
      {rotationFindings(rotation, keyCount).map((finding) => (
        <Alert key={finding.kind} tone={findingTone(finding)}>
          <FindingText finding={finding} />
        </Alert>
      ))}
    </div>
  );
}

function FindingText({ finding }: { finding: RotationFinding }) {
  const { t, tp } = useI18n();
  switch (finding.kind) {
    case "working":
      return t("adminSecurity.run.verdict.working");
    case "failed":
      return t("adminSecurity.run.verdict.failed", { error: finding.error || "—" });
    case "unreadable":
      return tp("adminSecurity.run.verdict.unreadable", finding.count);
    case "webhooks":
      return tp("adminSecurity.run.verdict.webhooks", finding.count);
    case "keysChanged":
      return tp("adminSecurity.run.verdict.keysChanged", Number(finding.then), { then: finding.then, now: finding.now });
    case "clean":
      return t(finding.isSingleKey ? "adminSecurity.run.verdict.cleanSingle" : "adminSecurity.run.verdict.clean");
  }
}

function RunFacts({ rotation }: { rotation: KeyRotation }) {
  const { t, locale } = useI18n();
  const viewer = useViewerFormat();
  const when = (value: number | null | undefined) => (value ? viewer.dateTime(value) : "—");
  const count = (value: number) => formatNumber(value, locale);
  return (
    <Facts
      columns={3}
      items={[
        {
          label: t("adminSecurity.run.facts.requested"),
          value: (
            <span className="inline-flex flex-wrap items-center gap-2">
              {when(rotation.requested_at)}
              <Badge tone={ROTATION_STATUS_TONES[rotation.status]}>{t(`adminSecurity.run.status.${rotation.status}`)}</Badge>
            </span>
          ),
        },
        { label: t("adminSecurity.run.facts.started"), value: when(rotation.started_at) },
        { label: t("adminSecurity.run.facts.finished"), value: when(rotation.finished_at) },
        { label: t("adminSecurity.run.facts.keys"), value: count(rotation.key_count) },
        { label: t("adminSecurity.run.facts.total"), value: count(rotation.secrets_total) },
        { label: t("adminSecurity.run.facts.current"), value: count(rotation.secrets_current) },
        { label: t("adminSecurity.run.facts.rotated"), value: count(rotation.secrets_rotated) },
        {
          label: t("adminSecurity.run.facts.unreadable"),
          value: (
            <span className={rotation.secrets_unreadable > 0 ? "text-danger" : undefined}>
              {count(rotation.secrets_unreadable)}
            </span>
          ),
        },
        { label: t("adminSecurity.run.facts.webhooksRenewed"), value: count(rotation.webhooks_renewed) },
        {
          label: t("adminSecurity.run.facts.webhooksFailed"),
          value: (
            <span className={rotation.webhooks_failed > 0 ? "text-warning" : undefined}>
              {count(rotation.webhooks_failed)}
            </span>
          ),
        },
      ]}
    />
  );
}
