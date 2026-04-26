import { endpoints, fetchJson } from './client'
import type { ProjectionPoint } from './mlDiagnosticsApi'

export interface QueryQuality {
  quality_status: string
  sharpness_score: number
  exposure_score: number
  glare_score: number
  issues: string[]
}

export interface QueryNeighbor {
  rank: number
  reference_image_id: string
  reference_item_id: string
  region_code: string
  label: string
  split: string
  similarity: number
}

export interface QueryProjection {
  query_point: { x: number; y: number; label: string }
  reference_points: ProjectionPoint[]
}

export interface QueryImageResult {
  query_id: string
  dataset_version: string
  model_version: string
  query_region_code: string | null
  search_scope: string
  available_region_codes: string[]
  quality: QueryQuality | null
  embedding: { dimension: number; norm: number } | null
  neighbors: QueryNeighbor[]
  projection: QueryProjection | null
  warnings: string[]
}

export async function queryImage(
  file: File,
  datasetVersion: string,
  modelVersion: string,
  k = 5,
  includeProjection = true,
  allowLowQuality = false,
  regionCode = '',
): Promise<QueryImageResult> {
  const form = new FormData()
  form.append('file', file)
  form.append('dataset_version', datasetVersion)
  form.append('model_version', modelVersion)
  form.append('k', String(k))
  form.append('include_projection', String(includeProjection))
  form.append('allow_low_quality', String(allowLowQuality))
  if (regionCode) form.append('region_code', regionCode)

  return fetchJson<QueryImageResult>(`${endpoints.diagnostics}/diagnostics/query-image`, {
    method: 'POST',
    body: form,
  })
}
