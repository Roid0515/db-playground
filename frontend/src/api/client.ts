/** Shared HTTP client: one place owning the API base URL, JSON parsing, and
 * error handling instead of every api/*.ts module repeating the same
 * fetch/response.ok/response.json() pattern.
 *
 * VITE_API_URL is "" for the desktop app build (same origin, relative
 * requests) and an absolute URL like http://localhost:8000 for the Docker
 * dev build -- apiUrl() works for both without callers needing to know which.
 */
export class ApiError extends Error {}

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export function apiUrl(path: string): string {
  return `${API_URL}${path}`;
}

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(
      typeof body?.detail === "string" ? body.detail : "요청을 처리하지 못했습니다.",
    );
  }
  return response.json() as Promise<T>;
}

export async function apiGet<T>(
  path: string,
  params?: Record<string, string | number>,
): Promise<T> {
  const query = params ? `?${new URLSearchParams(params as Record<string, string>)}` : "";
  const response = await fetch(apiUrl(path) + query);
  return parseJson<T>(response);
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(apiUrl(path), {
    method: "POST",
    headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  return parseJson<T>(response);
}
