"use client";

/**
 * What each detail card of /admin/system says in its folded row on a phone
 * (PhoneFold): the one figure or state on call looks for, in the danger or
 * warning colour when it wants a look (a stale worker, a circuit not
 * closed, dead jobs, a channel in error, differing payments, an open
 * incident). A card without such a figure folds with its name only.
 */

import type { ReactNode } from "react";

import { useI18n } from "@/i18n/client";

import { openCircuitCount } from "../../_lib/circuits";
import type { Incident } from "../../_lib/incidentForm";
import { hasMismatches } from "../../_lib/platformBrakes";
import { RUN_STATE_TONES, backupState, laneTone, type AdminSystem } from "../../_lib/system";
import { usePaymentReconciliation } from "../../_lib/usePlatformBrakes";
import { foldNote as noted, type FoldTone as Tone } from "../foldNote";
import { RUN_STATE_NAMES, useSystemFormat } from "./useSystemFormat";

export interface SystemFolds {
  workers: ReactNode;
  circuits: ReactNode;
  lanes: ReactNode;
  deadLetters: ReactNode;
  reconciliation: ReactNode;
  channels: ReactNode;
  backups: ReactNode;
  database: ReactNode;
  incidents: ReactNode;
}

function worstLaneTone(system: AdminSystem): Tone {
  const tones = system.lanes.map(laneTone);
  return tones.includes("danger") ? "danger" : tones.includes("warning") ? "warning" : null;
}

/** The folded rows' summaries of the System page; `incidents` is the loaded incident log (undefined while it loads). */
export function useSystemFolds(system: AdminSystem, incidents: readonly Incident[] | undefined): SystemFolds {
  const { t, tp } = useI18n();
  const format = useSystemFormat();
  const reconciliation = usePaymentReconciliation().data;

  const stale = system.workers.filter((worker) => worker.is_stale).length;
  const notClosed = openCircuitCount(system.circuits);
  const due = system.lanes.reduce((total, lane) => total + lane.waiting, 0);
  const deadJobs = system.dead_jobs.reduce((total, tally) => total + tally.count, 0);
  const expiring = system.expiring_credentials.length;
  const backup = backupState(system);
  const backupTone = RUN_STATE_TONES[backup];
  const openIncidents = incidents?.filter((incident) => incident.status === "open").length;

  return {
    workers:
      system.workers.length === 0
        ? noted(t("adminSystem.folds.none"), "danger")
        : stale > 0
          ? noted(tp("adminSystem.folds.stale", stale), "danger")
          : tp("adminSystem.folds.live", system.workers.length),
    circuits:
      system.circuits.length === 0
        ? null
        : notClosed > 0
          ? noted(tp("adminSystem.folds.notClosed", notClosed), "danger")
          : t("adminSystem.folds.allClosed"),
    lanes: system.lanes.length === 0 ? null : noted(tp("adminSystem.folds.due", due), worstLaneTone(system)),
    deadLetters: deadJobs > 0 ? noted(tp("adminSystem.folds.deadJobs", deadJobs), "danger") : t("adminSystem.folds.none"),
    reconciliation: !reconciliation?.ran_at
      ? null
      : hasMismatches(reconciliation)
        ? noted(t("platformBrakes.reconciliation.differs"), "danger")
        : t("adminSystem.folds.allMatch"),
    channels:
      system.channels_in_error_count > 0
        ? noted(tp("adminSystem.folds.inError", system.channels_in_error_count), "danger")
        : expiring > 0
          ? noted(tp("adminSystem.folds.expiring", expiring), "warning")
          : t("adminSystem.folds.noneInError"),
    backups: noted(t(RUN_STATE_NAMES[backup]), backupTone === "danger" || backupTone === "warning" ? backupTone : null),
    database: system.database_bytes === null || system.database_bytes === undefined ? null : format.bytes(system.database_bytes),
    incidents:
      openIncidents === undefined
        ? null
        : openIncidents > 0
          ? noted(tp("adminSystem.folds.open", openIncidents), "warning")
          : t("adminSystem.folds.noneOpen"),
  };
}
