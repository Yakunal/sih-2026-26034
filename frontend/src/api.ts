/*
  api.ts — every call to the backend, in one file.

  Plain `fetch`, no data-fetching library. Requests go to relative paths like
  /api/scan; Vite's dev proxy (see vite.config.ts) forwards them to FastAPI on
  port 8000.

  Note what is NOT here: the Gemini API key. The browser never sees it. The
  frontend asks our backend, and our backend is the only thing that talks to
  Gemini.
*/

import type {
  DemoProduct,
  Health,
  InspectionDetail,
  InspectionSummary,
  RulesResponse,
  ScanResponse,
  Stats,
  Status,
} from './types'

const BASE_URL = import.meta.env.VITE_API_URL || ''

/**
 * Run a request and turn a failure into a readable Error.
 *
 * FastAPI puts its message in a `detail` field, so a missing API key reaches
 * the user as "GEMINI_API_KEY is not set..." rather than "HTTP 503".
 */
async function request<T>(url: string, options?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE_URL}${url}`, options)
  } catch {
    throw new Error('Could not reach the backend. Is it running on port 8000?')
  }

  if (!response.ok) {
    let detail = `Request failed (HTTP ${response.status}).`
    try {
      const body = await response.json()
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      // The error body was not JSON; the generic message above will do.
    }
    throw new Error(detail)
  }

  return response.json() as Promise<T>
}

export const getHealth = () => request<Health>('/api/health')

export const getStats = () => request<Stats>('/api/stats')

export const getRules = () => request<RulesResponse>('/api/rules')

export const getDemoProducts = () => request<DemoProduct[]>('/api/demo-products')

export const getInspection = (id: number) => request<InspectionDetail>(`/api/inspections/${id}`)

export const getInspections = (status?: Status) =>
  request<InspectionSummary[]>(`/api/inspections${status ? `?status=${status}` : ''}`)

/** Upload a real photograph. Needs GEMINI_API_KEY on the server. */
export function scanImage(file: File) {
  const form = new FormData()
  form.append('image', file)
  return request<ScanResponse>('/api/scan', { method: 'POST', body: form })
}

/**
 * Run a prepared demo product.
 *
 * live = false (default) uses the cached extraction of that image.
 * live = true sends the same image to Gemini for a genuine reading.
 * Either way the rule engine, scoring and database write run for real.
 */
export const scanDemoProduct = (id: string, live = false) =>
  request<ScanResponse>(`/api/demo-products/${id}/scan?live=${live}`, { method: 'POST' })

/** The PDF is a plain download, so we just need its URL. */
export const reportUrl = (id: number) => `${BASE_URL}/api/inspections/${id}/report`
