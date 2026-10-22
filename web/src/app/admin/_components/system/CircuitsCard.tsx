"use client";

import { Badge, Card, EmptyState, TBody, THead, Td, Th, Tr } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { ScrollingTable } from "../metrics/ScrollingTable";
import { CIRCUIT_STATE_TONES, circuitProvider, type CircuitSummary } from "../../_lib/circuits";
import { useSystemFormat } from "./useSystemFormat";

/**
 * The circuit breakers of the live workers, one row per circuit: the
 * providers the platform sends through (and the language models), the worst
 * state any worker reports, in how many workers it is not closed, the
 * failures of the last minute and since when the earliest is open. The API
 * lists the circuits that are not closed first.
 */
export function CircuitsCard({ circuits }: { circuits: readonly CircuitSummary[] }) {
  const { t } = useI18n();
  const format = useSystemFormat();
  const title = t("providerCircuits.title");
  return (
    <Card aria-label={title} title={title} description={t("providerCircuits.description")} padded={circuits.length === 0}>
      {circuits.length === 0 ? (
        <EmptyState title={t("providerCircuits.none")} description={t("providerCircuits.noneDescription")} />
      ) : (
        <ScrollingTable caption={title}>
          <THead>
            <Tr>
              <Th>{t("providerCircuits.circuit")}</Th>
              <Th>{t("providerCircuits.state")}</Th>
              <Th align="right">{t("providerCircuits.workers")}</Th>
              <Th align="right">{t("providerCircuits.failures")}</Th>
              <Th>{t("providerCircuits.opened")}</Th>
            </Tr>
          </THead>
          <TBody>
            {circuits.map((circuit) => {
              const provider = circuitProvider(circuit.circuit);
              const isClosed = circuit.state === "closed";
              return (
                <Tr key={circuit.circuit}>
                  <Th scope="row" className="py-3 font-medium text-ink">
                    {provider ? (
                      t(`providerCircuits.providers.${provider}`)
                    ) : (
                      <span className="font-mono text-xs break-all">{circuit.circuit}</span>
                    )}
                  </Th>
                  <Td>
                    <Badge tone={CIRCUIT_STATE_TONES[circuit.state]}>{t(`providerCircuits.states.${circuit.state}`)}</Badge>
                  </Td>
                  <Td align="right" className={cn("whitespace-nowrap", !isClosed && "font-semibold text-danger")}>
                    {t("providerCircuits.workersOf", {
                      notClosed: format.number(circuit.workers_not_closed),
                      total: format.number(circuit.workers_reporting),
                    })}
                  </Td>
                  <Td align="right" className={cn(circuit.recent_failures > 0 && "font-semibold text-warning")}>
                    {format.number(circuit.recent_failures)}
                  </Td>
                  <Td className="whitespace-nowrap text-ink-muted">{format.when(circuit.opened_at)}</Td>
                </Tr>
              );
            })}
          </TBody>
        </ScrollingTable>
      )}
    </Card>
  );
}
