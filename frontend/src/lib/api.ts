import { supabase } from './supabase'

const BASE_URL   = import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:8005'
const ALERTS_URL = import.meta.env.VITE_ALERTS_URL  ?? 'http://localhost:8004'
const DATA_URL   = import.meta.env.VITE_DATA_URL    ?? 'http://localhost:8003'

async function buildHeaders(extra?: HeadersInit): Promise<HeadersInit> {
  const { data: { session } } = await supabase.auth.getSession()
  return {
    'Content-Type': 'application/json',
    ...(session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {}),
    ...extra,
  }
}

/** Accounts service (port 8005) */
export async function backendFetch(path: string, options: RequestInit = {}): Promise<Response> {
  return fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: await buildHeaders(options.headers),
  })
}

/** Alerts service (port 8004) */
export async function alertsFetch(path: string, options: RequestInit = {}): Promise<Response> {
  return fetch(`${ALERTS_URL}${path}`, {
    ...options,
    headers: await buildHeaders(options.headers),
  })
}

/** Data processing service (port 8003) */
export async function dataFetch(path: string, options: RequestInit = {}): Promise<Response> {
  return fetch(`${DATA_URL}${path}`, {
    ...options,
    headers: await buildHeaders(options.headers),
  })
}
