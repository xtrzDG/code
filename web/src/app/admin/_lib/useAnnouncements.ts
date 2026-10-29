"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { Schema } from "@/api/types";
import { useCursorPage } from "@/api/useCursorPage";
import { useMutation } from "@/api/useMutation";

import type { AdminAnnouncement, CreateAnnouncementBody, UpdateAnnouncementBody } from "./announcementForm";

const ANNOUNCEMENTS_PAGE_SIZE = 10;

/**
 * The status page's announcements (GET /v1/admin/announcements, newest
 * first), publishing one and changing or resolving it. Each change is
 * audited and needs a recent sign-in: the API client asks for the code and
 * sends it again. The public status page and the banners pick it up within
 * a minute.
 */
export function useAnnouncements() {
  const announcements = useCursorPage<AdminAnnouncement, Schema<"AnnouncementPage">>(
    queryKeys.admin.announcements(),
    ({ cursor, limit }) =>
      api.GET("/v1/admin/announcements", { params: { query: { limit: String(limit), cursor: cursor ?? undefined } } }),
    { pageSize: ANNOUNCEMENTS_PAGE_SIZE },
  );
  const { updateItems } = announcements;
  const creation = useMutation((body: CreateAnnouncementBody) => api.POST("/v1/admin/announcements", { body }), {
    errorToast: false,
  });
  const change = useMutation(
    (id: string, body: UpdateAnnouncementBody) =>
      api.PATCH("/v1/admin/announcements/{announcement_id}", { params: { path: { announcement_id: id } }, body }),
    { errorToast: false },
  );

  const keep = (announcement: AdminAnnouncement) =>
    updateItems((items) => [announcement, ...items.filter((item) => item.id !== announcement.id)].sort((a, b) => b.created_at - a.created_at));

  /** The published announcement, or null (the error is in `creation.error`). */
  const publish = async (body: CreateAnnouncementBody): Promise<AdminAnnouncement | null> => {
    const result = await creation.run(body);
    if (!result.ok) {
      return null;
    }
    keep(result.data);
    return result.data;
  };

  const update = async (id: string, body: UpdateAnnouncementBody): Promise<AdminAnnouncement | null> => {
    const result = await change.run(id, body);
    if (!result.ok) {
      return null;
    }
    keep(result.data);
    return result.data;
  };

  return { announcements, publish, update, creation, change };
}
