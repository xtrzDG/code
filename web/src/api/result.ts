import { parseApiError, toApiError } from "./errors";

/** What openapi-fetch resolves to: data on success, error otherwise. */
export interface ApiResult<T> {
  data?: T;
  error?: unknown;
  response: Response;
}

/**
 * The data of an openapi-fetch call, or a thrown ApiError:
 *
 *     const business = await unwrap(api.GET("/v1/businesses/{business_id}", {...}));
 *
 * Works the same in the browser (`api`) and on the server (`getServerApi()`).
 */
export async function unwrap<T>(request: Promise<ApiResult<T>>): Promise<T> {
  let result: ApiResult<T>;
  try {
    result = await request;
  } catch (error) {
    throw toApiError(error);
  }

  const { response } = result;
  if (!response.ok || result.error !== undefined) {
    throw parseApiError(response.status, result.error, response.headers.get("x-request-id"));
  }
  return result.data as T;
}
