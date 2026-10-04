"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { Schema } from "@/api/types";
import { useCursorPage } from "@/api/useCursorPage";
import { useMutation } from "@/api/useMutation";

import type { CreateIncidentBody, Incident } from "./incidentForm";

const INCIDENTS_PAGE_SIZE = 10;

/**
 * The incident log (GET /v1/admin/incidents, newest first) and recording
 * one (POST: audit entries for the businesses, and for a data breach the
 * DPA 12.1 notice to their owners). The request needs a recent sign-in: the
 * API client asks for the code and sends it again.
 */
export function useIncidents() {
  const incidents = useCursorPage<Incident, Schema<"IncidentPage">>(
    queryKeys.admin.incidents(),
    ({ cursor, limit }) => api.GET("/v1/admin/incidents", { params: { query: { limit: String(limit), cursor: cursor ?? undefined } } }),
    { pageSize: INCIDENTS_PAGE_SIZE },
  );
  const { updateItems } = incidents;
  const create = useMutation((body: CreateIncidentBody) => api.POST("/v1/admin/incidents", { body }), { errorToast: false });

  /** The recorded incident, or null (the error is in `createError`). */
  const record = async (body: CreateIncidentBody): Promise<Incident | null> => {
    const result = await create.run(body);
    if (!result.ok) {
      return null;
    }
    updateItems((items) => [result.data, ...items.filter((item) => item.id !== result.data.id)]);
    return result.data;
  };

  return { incidents, record, isRecording: create.isPending, createError: create.error };
}
