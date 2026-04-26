import { endpoints, fetchJson } from './client'

export interface DatasetSummary {
  id: string
  dataset_version: string
  status: string
  source_type: string
  created_at: string
  image_count: number
  train_count: number
  validation_count: number
  test_count: number
}

export interface DatasetDetail extends DatasetSummary {
  splits: Record<string, number>
  region_codes: string[]
  label_values: string[]
  embedding_models: string[]
}

export interface ModelSummary {
  id: string
  model_name: string
  model_version: string
  model_type: string
  artifact_uri?: string
  is_active: boolean
  created_at: string
}

export interface EvaluationRun {
  id: string
  evaluation_name: string
  embedding_model_version: string
  reference_dataset_version: string
  threshold_profile: string
  status: string
  summary_json: Record<string, unknown> | null
  started_at: string
  completed_at?: string
}

export interface ProjectionPoint {
  reference_image_id: string
  x: number
  y: number
  label: string
  region_code: string
  split: string
}

export interface NeighborEntry {
  id: string
  label: string
  similarity: number
}

export interface NeighborItem {
  reference_image_id: string
  expected_label: string
  region_code: string
  nn_agrees: boolean
  neighbors: NeighborEntry[]
}

export interface NeighborResult {
  dataset_version: string
  model_version: string
  k: number
  total: number
  nn_agreement: number
  nn_agreement_rate: number
  items: NeighborItem[]
}

export interface EmbeddingAnalysis {
  dataset_version: string
  model_version: string
  dataset_scoped?: boolean
  count: number
  dimension: number
  norm_mean: number
  norm_min: number
  norm_max: number
  pairwise_mean: number
  pairwise_min: number
  pairwise_max: number
  intra_class_mean: number
  inter_class_mean: number
  cluster_separation: number
  pairs_sampled: number
  region_counts: Record<string, { total: number }>
  unique_labels: string[]
}

export async function listDatasets(): Promise<DatasetSummary[]> {
  return fetchJson(`${endpoints.diagnostics}/datasets`)
}

export async function getDataset(version: string): Promise<DatasetDetail> {
  return fetchJson(`${endpoints.diagnostics}/datasets/${version}`)
}

export async function listModels(): Promise<ModelSummary[]> {
  return fetchJson(`${endpoints.diagnostics}/models`)
}

export async function listEvaluations(): Promise<EvaluationRun[]> {
  return fetchJson(`${endpoints.diagnostics}/evaluations`)
}

export async function getEvaluation(id: string): Promise<EvaluationRun & { items: unknown[] }> {
  return fetchJson(`${endpoints.diagnostics}/evaluations/${id}`)
}

export async function getProjections(dataset: string, model: string): Promise<ProjectionPoint[]> {
  return fetchJson(`${endpoints.diagnostics}/projections?dataset_version=${encodeURIComponent(dataset)}&model_version=${encodeURIComponent(model)}`)
}

export async function getNeighbors(dataset: string, model: string, k = 5): Promise<NeighborResult> {
  return fetchJson(`${endpoints.diagnostics}/neighbors?dataset_version=${encodeURIComponent(dataset)}&model_version=${encodeURIComponent(model)}&k=${k}`)
}

export async function getEmbeddingAnalysis(dataset: string, model: string, includeOutOfDataset = false): Promise<EmbeddingAnalysis> {
  const params = new URLSearchParams({ dataset_version: dataset, model_version: model })
  if (includeOutOfDataset) params.set('include_out_of_dataset', 'true')
  return fetchJson(`${endpoints.diagnostics}/embedding-analysis?${params}`)
}

export interface DatasetModelCompat {
  model_name: string
  model_version: string
  embedding_count: number
  image_count: number
  compatible: boolean
}

export async function getDatasetModels(dataset: string): Promise<DatasetModelCompat[]> {
  return fetchJson(`${endpoints.diagnostics}/datasets/${encodeURIComponent(dataset)}/models`)
}
