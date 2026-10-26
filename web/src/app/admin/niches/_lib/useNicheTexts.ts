"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";

import type { DraftBody, NicheTextRelease } from "./nicheTexts";

/** Every niche's override state, named in the admin's language (GET /v1/admin/niche-templates). */
export function useNicheOverview(language: string) {
  return useQuery(queryKeys.admin.niches(language), () =>
    api.GET("/v1/admin/niche-templates", { params: { query: { language } } }),
  );
}

/**
 * One niche's editor in one language of its texts, its versions, and the
 * changes: saving the language's draft answers the editor, which replaces
 * it; publishing, a restore and discarding the draft reload the niche in
 * every language, its versions and the overview. Publishing and restoring
 * may first ask to confirm with a code (step-up, handled by the API
 * client). Each change resolves to its result, or null when it failed.
 */
export function useNicheEditor(nicheKey: string, language: string) {
  const path = { niche_key: nicheKey };
  const editor = useQuery(queryKeys.admin.niche(nicheKey, language), () =>
    api.GET("/v1/admin/niche-templates/{niche_key}", { params: { path, query: { language } } }),
  );
  const versions = useQuery(queryKeys.admin.nicheVersions(nicheKey), () =>
    api.GET("/v1/admin/niche-templates/{niche_key}/versions", { params: { path } }),
  );
  const reload = [["admin", "niche", nicheKey], ["admin", "niches"]] as const;
  const saving = useMutation((body: DraftBody) => api.PUT("/v1/admin/niche-templates/{niche_key}/draft", { params: { path }, body }), {
    invalidate: [["admin", "niches"]],
  });
  const publishing = useMutation(() => api.POST("/v1/admin/niche-templates/{niche_key}/publish", { params: { path } }), {
    invalidate: reload,
  });
  const restoring = useMutation(
    (version: number) => api.POST("/v1/admin/niche-templates/{niche_key}/revert", { params: { path }, body: { version } }),
    { invalidate: reload },
  );
  const discarding = useMutation(() => api.DELETE("/v1/admin/niche-templates/{niche_key}/draft", { params: { path } }), {
    invalidate: reload,
  });

  const save = async (body: DraftBody): Promise<boolean> => {
    const result = await saving.run(body);
    if (result.ok) {
      editor.setData(result.data);
    }
    return result.ok;
  };
  const publish = async (): Promise<NicheTextRelease | null> => {
    const result = await publishing.run();
    return result.ok ? result.data : null;
  };
  const restore = async (version: number): Promise<NicheTextRelease | null> => {
    const result = await restoring.run(version);
    return result.ok ? result.data : null;
  };
  const discard = async (): Promise<boolean> => (await discarding.run()).ok;

  return { editor, versions, save, saving, publish, publishing, restore, restoring, discard, discarding };
}
