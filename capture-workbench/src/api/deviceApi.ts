import { endpoints, fetchJson } from './client'
import type { DeviceRegisterRequest, DeviceResponse, CalibrationRequest, CalibrationResponse } from './types'

export async function registerDevice(req: DeviceRegisterRequest): Promise<DeviceResponse> {
  return fetchJson<DeviceResponse>(`${endpoints.device}/devices/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
}

export async function getDevice(deviceId: string): Promise<DeviceResponse> {
  return fetchJson<DeviceResponse>(`${endpoints.device}/devices/${deviceId}`)
}

export async function createCalibration(deviceId: string, req: CalibrationRequest): Promise<CalibrationResponse> {
  return fetchJson<CalibrationResponse>(`${endpoints.device}/devices/${deviceId}/calibrations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
}
