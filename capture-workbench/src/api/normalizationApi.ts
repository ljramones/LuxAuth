import { endpoints, fetchJson } from './client'
import type { NormalizationResult } from './types'

export async function getNormalizationResult(imageAssetId: string): Promise<NormalizationResult | null> {
  try {
    return await fetchJson<NormalizationResult>(`${endpoints.normalization}/results/${imageAssetId}`)
  } catch {
    return null
  }
}
