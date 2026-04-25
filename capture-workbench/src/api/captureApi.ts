import { endpoints, fetchJson } from './client'
import type {
  CaptureProtocol,
  CreateCaptureSessionRequest,
  CaptureSessionResponse,
  SessionStatusResponse,
  ImageUploadResponse,
  CompleteSessionResponse,
} from './types'

export async function listProtocols(): Promise<CaptureProtocol[]> {
  return fetchJson<CaptureProtocol[]>(`${endpoints.capture}/capture-protocols`)
}

export async function getProtocol(code: string): Promise<CaptureProtocol> {
  return fetchJson<CaptureProtocol>(`${endpoints.capture}/capture-protocols/${code}`)
}

export async function createSession(req: CreateCaptureSessionRequest): Promise<CaptureSessionResponse> {
  return fetchJson<CaptureSessionResponse>(`${endpoints.capture}/capture-sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
}

export async function getSessionStatus(sessionId: string): Promise<SessionStatusResponse> {
  return fetchJson<SessionStatusResponse>(`${endpoints.capture}/capture-sessions/${sessionId}/status`)
}

export async function uploadImage(
  sessionId: string,
  file: File,
  fields: Record<string, string>,
): Promise<ImageUploadResponse> {
  const form = new FormData()
  form.append('file', file)
  for (const [k, v] of Object.entries(fields)) {
    form.append(k, v)
  }
  return fetchJson<ImageUploadResponse>(`${endpoints.capture}/capture-sessions/${sessionId}/images`, {
    method: 'POST',
    body: form,
  })
}

export async function completeSession(sessionId: string): Promise<CompleteSessionResponse> {
  return fetchJson<CompleteSessionResponse>(`${endpoints.capture}/capture-sessions/${sessionId}/complete`, {
    method: 'POST',
  })
}
