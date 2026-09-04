import { createBrowserClient } from "@supabase/ssr";

export const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type IdentityView = {
  email: string;
  is_admin: boolean;
  workspace_id: string | null;
  workspace_status: string | null;
};

export function supabaseBrowser() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) return null;
  return createBrowserClient(url, key);
}

export async function deskFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const supabase = supabaseBrowser();
  if (!supabase) throw new Error("Supabase public configuration is not available.");
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (!token) throw new Error("Sign in to access the Connected Paper workspace.");
  const response = await fetch(`${apiBase}/api/v1${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(body?.detail ?? `Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
