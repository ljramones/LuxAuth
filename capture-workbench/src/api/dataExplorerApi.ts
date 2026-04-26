import { endpoints, fetchJson } from './client'

export interface DataOverview {
  datasets: number
  reference_items: number
  reference_images: number
  embeddings: number
  capture_batches: number
  quality_reports_pass: number
  quality_reports_fail: number
  condition_metadata: number
  component_conditions: number
  datasets_by_status: Record<string, number>
  datasets_by_source: Record<string, number>
  embeddings_by_model: Record<string, number>
}

export interface DatasetRow {
  id: string
  dataset_version: string
  status: string
  source_type: string
  created_at: string
  image_count: number
  item_count: number
  train_count: number
  validation_count: number
  test_count: number
  region_codes: string[]
  label_values: string[]
  embedding_counts_by_model: Record<string, number>
}

export interface DatasetStats {
  dataset_version: string
  status: string
  source_type: string
  splits: Record<string, number>
  region_counts: Record<string, number>
  label_counts: Record<string, number>
  embedding_counts_by_model: Record<string, number>
  condition_grades: Record<string, number>
  component_statuses: Record<string, number>
}

export interface DataWarning {
  severity: string
  type: string
  message: string
  affected_count: number
  recommended_action: string
}

export interface DatasetImage {
  reference_image_id: string
  reference_item_id: string
  region_code: string
  object_uri: string
  created_at: string
  split: string
  authenticity_status: string
}

export interface DatasetItem {
  reference_item_id: string
  authenticity_status: string
  brand: string
  category: string
  material: string
  source: string
  label_confidence: string
  image_count: number
  split: string
  condition_grade: string | null
  known_repairs: boolean
  third_party_repair: boolean
}

export async function getOverview(): Promise<DataOverview> {
  return fetchJson(`${endpoints.diagnostics}/data/overview`)
}

export async function getDatasets(): Promise<DatasetRow[]> {
  return fetchJson(`${endpoints.diagnostics}/data/datasets`)
}

export async function getDatasetStats(dv: string): Promise<DatasetStats> {
  return fetchJson(`${endpoints.diagnostics}/data/datasets/${encodeURIComponent(dv)}/stats`)
}

export async function getDatasetWarnings(dv: string): Promise<DataWarning[]> {
  return fetchJson(`${endpoints.diagnostics}/data/datasets/${encodeURIComponent(dv)}/warnings`)
}

export async function getDatasetImages(dv: string, params: Record<string, string> = {}): Promise<{ total: number; images: DatasetImage[] }> {
  const qs = new URLSearchParams(params)
  return fetchJson(`${endpoints.diagnostics}/data/datasets/${encodeURIComponent(dv)}/images?${qs}`)
}

export async function getDatasetItems(dv: string): Promise<DatasetItem[]> {
  return fetchJson(`${endpoints.diagnostics}/data/datasets/${encodeURIComponent(dv)}/items`)
}
