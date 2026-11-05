"use client";

/**
 * Reading and changing brands (chains of locations). Every change marks
 * all brand reads out of date: a brand's team, locations and shared
 * answers show on several of its pages at once.
 */

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { RequestBody } from "@/api/types";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";

import type { InviteBody } from "./brands";

export type BrandPeriod = "7d" | "30d" | "90d";
export const BRAND_PERIODS: readonly BrandPeriod[] = ["7d", "30d", "90d"];

export type KnowledgeBody = RequestBody<"/v1/brands/{brand_id}/knowledge", "post">;
type CloneBody = RequestBody<"/v1/brands/{brand_id}/locations/clone", "post">;

const everyBrandRead = [queryKeys.brands.all()];

/** The brands the signed-in person belongs to (GET /v1/brands). */
export function useMyBrands() {
  return useQuery(queryKeys.brands.mine(), () => api.GET("/v1/brands"));
}

/** One brand: its locations and, for owners, its team. */
export function useBrand(brandId: string) {
  return useQuery(queryKeys.brands.detail(brandId), () =>
    api.GET("/v1/brands/{brand_id}", { params: { path: { brand_id: brandId } } }),
  );
}

/** Each reached location's value, sources and waiting work over a period. */
export function useBrandDashboard(brandId: string, period: BrandPeriod) {
  return useQuery(
    queryKeys.brands.dashboard(brandId, period),
    () => api.GET("/v1/brands/{brand_id}/dashboard", { params: { path: { brand_id: brandId }, query: { period } } }),
    { keepPreviousData: true },
  );
}

/** The facts every location shares, with the locations that replace each. */
export function useBrandKnowledge(brandId: string) {
  return useQuery(queryKeys.brands.knowledge(brandId), () =>
    api.GET("/v1/brands/{brand_id}/knowledge", { params: { path: { brand_id: brandId } } }),
  );
}

/** Starting a brand from one business the person owns. */
export function useCreateBrand() {
  return useMutation(
    (name: string, businessId: string) => api.POST("/v1/brands", { body: { name, business_id: businessId } }),
    { errorToast: false, invalidate: everyBrandRead },
  );
}

/** The brand's name, its existence and its locations (brand owners). */
export function useBrandSettings(brandId: string) {
  const path = { brand_id: brandId };
  const options = { errorToast: false, invalidate: everyBrandRead } as const;
  return {
    rename: useMutation((name: string) => api.PATCH("/v1/brands/{brand_id}", { params: { path }, body: { name } }), options),
    remove: useMutation(() => api.DELETE("/v1/brands/{brand_id}", { params: { path } }), options),
    addLocation: useMutation(
      (businessId: string) => api.POST("/v1/brands/{brand_id}/locations", { params: { path }, body: { business_id: businessId } }),
      options,
    ),
    removeLocation: useMutation(
      (businessId: string) =>
        api.DELETE("/v1/brands/{brand_id}/locations/{business_id}", { params: { path: { ...path, business_id: businessId } } }),
      { invalidate: everyBrandRead },
    ),
    cloneLocation: useMutation(
      (body: CloneBody) => api.POST("/v1/brands/{brand_id}/locations/clone", { params: { path }, body }),
      options,
    ),
  };
}

/** The brand's team: invitations, roles and departures. */
export function useBrandTeam(brandId: string) {
  const path = { brand_id: brandId };
  return {
    invite: useMutation(
      (body: InviteBody) => api.POST("/v1/brands/{brand_id}/members", { params: { path }, body }),
      { errorToast: false, invalidate: everyBrandRead },
    ),
    change: useMutation(
      (userId: string, body: Pick<InviteBody, "role" | "business_ids">) =>
        api.PATCH("/v1/brands/{brand_id}/members/{user_id}", { params: { path: { ...path, user_id: userId } }, body }),
      { errorToast: false, invalidate: everyBrandRead },
    ),
    remove: useMutation(
      (userId: string) => api.DELETE("/v1/brands/{brand_id}/members/{user_id}", { params: { path: { ...path, user_id: userId } } }),
      { errorToast: false, invalidate: everyBrandRead },
    ),
  };
}

/** The answers every location shares (brand owners). */
export function useBrandKnowledgeActions(brandId: string) {
  const path = { brand_id: brandId };
  const knowledge = [queryKeys.brands.knowledge(brandId)];
  return {
    create: useMutation(
      (body: KnowledgeBody) => api.POST("/v1/brands/{brand_id}/knowledge", { params: { path }, body }),
      { errorToast: false, invalidate: knowledge },
    ),
    update: useMutation(
      (sharedKey: string, body: KnowledgeBody) =>
        api.PUT("/v1/brands/{brand_id}/knowledge/{shared_key}", { params: { path: { ...path, shared_key: sharedKey } }, body }),
      { errorToast: false, invalidate: knowledge },
    ),
    remove: useMutation(
      (sharedKey: string) =>
        api.DELETE("/v1/brands/{brand_id}/knowledge/{shared_key}", { params: { path: { ...path, shared_key: sharedKey } } }),
      { invalidate: knowledge },
    ),
  };
}
