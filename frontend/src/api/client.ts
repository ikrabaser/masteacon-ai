// Thin fetch wrapper: attaches the Bearer token, refreshes it silently on a
// 401 via the HttpOnly refresh cookie, parses JSON, and normalizes errors.

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const REFRESH_PATH = "/api/v1/auth/refresh";
// Never attempt a silent refresh for these - refresh itself must not retry
// itself, and a 401 from login/register is a real credential/verification
// failure the caller needs to see, not something a refresh could fix.
const NO_REFRESH_RETRY_PATHS = new Set([REFRESH_PATH, "/api/v1/auth/login", "/api/v1/auth/register"]);

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

let authToken: string | null = null;
let onTokenRefreshed: ((token: string) => void) | null = null;
let refreshInFlight: Promise<string> | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
}

// AuthContext registers a callback here so a token refreshed transparently
// mid-request also gets persisted (localStorage) and reflected in its state
// - the rest of the app never needs to know a refresh happened at all.
export function setOnTokenRefreshed(handler: ((token: string) => void) | null): void {
  onTokenRefreshed = handler;
}

interface RequestOptions {
  method?: string;
  json?: unknown;
  formData?: FormData;
  query?: Record<string, string | number | undefined>;
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  // `new URL()` throws on a bare relative string with no base — pass
  // window.location.origin explicitly so an empty API_BASE_URL (same-origin
  // deployments, see docker-compose.yml's VITE_API_BASE_URL) still resolves.
  const url = new URL(`${API_BASE_URL}${path}`, window.location.origin);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined) url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

async function refreshAccessToken(): Promise<string> {
  // Coalesce concurrent 401s (e.g. several requests firing at once when the
  // access token expires) into a single refresh call instead of racing
  // several rotations against each other, which would have every request
  // but the first lose the replay-detection race.
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      const response = await fetch(buildUrl(REFRESH_PATH), { method: "POST", credentials: "include" });
      if (!response.ok) throw new ApiError("Session expired.", response.status);
      const body = (await response.json()) as { access_token: string };
      authToken = body.access_token;
      onTokenRefreshed?.(body.access_token);
      return body.access_token;
    })().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (authToken) headers["Authorization"] = `Bearer ${authToken}`;

  let body: BodyInit | undefined;
  if (options.formData) {
    body = options.formData;
  } else if (options.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.json);
  }

  const method = options.method ?? (body ? "POST" : "GET");
  const url = buildUrl(path, options.query);
  // Sent on every request; the refresh cookie itself is scoped server-side
  // to /api/v1/auth so it's only ever actually attached to those calls -
  // this just lets the browser honor Set-Cookie/attach it at all, which
  // fetch requires explicitly for cross-origin requests (local dev has the
  // frontend and API on different ports).
  const doFetch = () => fetch(url, { method, headers, body, credentials: "include" });

  let response = await doFetch();

  if (response.status === 401 && !NO_REFRESH_RETRY_PATHS.has(path)) {
    try {
      const newToken = await refreshAccessToken();
      headers["Authorization"] = `Bearer ${newToken}`;
      response = await doFetch();
    } catch {
      // Refresh failed (no session, expired, replayed) - fall through and
      // let the original 401 propagate; the caller (AuthContext) treats any
      // unrecovered 401 from getCurrentUser as "not logged in".
    }
  }

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const errorBody = await response.json();
      if (typeof errorBody?.detail === "string") detail = errorBody.detail;
    } catch {
      // response wasn't JSON — keep the generic message
    }
    throw new ApiError(detail, response.status);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
