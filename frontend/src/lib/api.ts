import { supabase } from './supabase'

const BASE_URL = import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:8000'

/**
 * Fetch wrapper that automatically attaches the current user's Supabase JWT
 * as an Authorization header. Use this for all calls to the Python backend.
 */
export async function backendFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const { data: { session } } = await supabase.auth.getSession()

  return fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(session?.access_token
        ? { Authorization: `Bearer ${session.access_token}` }
        : {}),
      ...options.headers,
    },
  })
}
