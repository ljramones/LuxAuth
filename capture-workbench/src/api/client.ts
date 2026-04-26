const DEVICE_URL = import.meta.env.VITE_DEVICE_SERVICE_URL || 'http://localhost:8103'
const CAPTURE_URL = import.meta.env.VITE_CAPTURE_INTAKE_SERVICE_URL || 'http://localhost:8106'
const QUALITY_URL = import.meta.env.VITE_IMAGE_QUALITY_SERVICE_URL || 'http://localhost:8201'
const NORMALIZATION_URL = import.meta.env.VITE_NORMALIZATION_SERVICE_URL || 'http://localhost:8202'
const DIAGNOSTICS_URL = import.meta.env.VITE_ML_DIAGNOSTICS_SERVICE_URL || 'http://localhost:8401'

export const endpoints = {
  device: DEVICE_URL,
  capture: CAPTURE_URL,
  quality: QUALITY_URL,
  normalization: NORMALIZATION_URL,
  diagnostics: DIAGNOSTICS_URL,
}

export async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status}: ${text}`)
  }
  return res.json()
}

export async function checkHealth(baseUrl: string): Promise<{ ok: boolean; service?: string }> {
  try {
    const data = await fetchJson<{ status: string; service: string }>(`${baseUrl}/health`)
    return { ok: data.status === 'healthy' || data.status === 'ok', service: data.service }
  } catch {
    return { ok: false }
  }
}
