import type { ApiError } from "@/api/errors";
import { refusalReasons, type Refusal } from "@/lib/assistant/goLive";

export interface RefusalState {
  reasons: Refusal[];
  error: ApiError;
}

/** A refused publish or rollback (409, or 403 for a forced publish), else null. */
export function refusalOf(error: ApiError): RefusalState | null {
  return error.status === 409 || error.status === 403 ? { reasons: refusalReasons(error), error } : null;
}
