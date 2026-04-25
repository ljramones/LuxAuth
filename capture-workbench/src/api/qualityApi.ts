import { endpoints, fetchJson } from './client'
import type { QualityReport } from './types'

export async function getQualityReport(imageAssetId: string): Promise<QualityReport | null> {
  try {
    return await fetchJson<QualityReport>(`${endpoints.quality}/reports/${imageAssetId}`)
  } catch {
    return null
  }
}
