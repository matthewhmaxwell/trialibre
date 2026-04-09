/**
 * Centralized API client.
 * All API calls should go through this module instead of hardcoding /api/v1/ URLs.
 */

const BASE = '/api/v1';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, init);
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: `HTTP ${resp.status}` }));
    throw new Error(err.detail || `HTTP ${resp.status}`);
  }
  return resp.json();
}

export const api = {
  health: () => request('/health'),
  privacyStatus: () => request('/privacy/status'),
  settings: {
    get: () => request('/settings'),
    update: (body: Record<string, unknown>) => request('/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  },
  match: (body: Record<string, unknown>) => request('/match', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }),
  trials: {
    list: (params?: { offset?: number; limit?: number }) =>
      request(`/trials?offset=${params?.offset ?? 0}&limit=${params?.limit ?? 200}`),
    get: (nctId: string) => request(`/trials/${encodeURIComponent(nctId)}`),
    delete: (nctId: string) => request(`/trials/${encodeURIComponent(nctId)}`, { method: 'DELETE' }),
  },
  batch: {
    start: (body: Record<string, unknown>) => request('/batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
    status: (jobId: string) => request(`/batch/${encodeURIComponent(jobId)}`),
  },
  referrals: {
    list: () => request('/referrals'),
    create: (body: Record<string, unknown>) => request('/referrals', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  },
  ingest: {
    trial: (formData: FormData) => fetch(`${BASE}/ingest/trial`, { method: 'POST', body: formData }),
    ctgov: (nctId: string) => request(`/ingest/ctgov/${encodeURIComponent(nctId)}`, { method: 'POST' }),
  },
  sandbox: {
    patients: () => request('/sandbox/patients'),
    protocols: () => request('/sandbox/protocols'),
  },
  dashboard: () => request('/dashboard/summary'),
};
