/**
 * The operations routes (bookings, leads) read their JSON bodies themselves,
 * so openapi.json declares no request body and the typed client refuses a
 * `body`. This adds one, typed by the caller (see ManualBookingBody & co. in
 * ./types.ts); openapi-fetch sends it as JSON like any other body.
 *
 *     api.PATCH("/v1/businesses/{business_id}/leads/{lead_id}",
 *       withJsonBody({ params: { path: {...} } }, body satisfies LeadStatusBody));
 */
export function withJsonBody<Init extends object>(init: Init, body: object): Init {
  return { ...init, body } as Init;
}
