import { useState } from 'react'
import { getEmbeddingAnalysis, type EmbeddingAnalysis } from '../api/mlDiagnosticsApi'

interface Props {
  dataset: string | null
  model: string | null
  expectedEmbeddingCount?: number
  onResult?: (a: EmbeddingAnalysis) => void
}

const KNOWN_REGIONS = new Set([
  'EXTERIOR_CANVAS', 'FRONT_LOGO_PRINT', 'INTERIOR_HEAT_STAMP',
  'HARDWARE_ENGRAVING', 'STITCHING_DETAIL', 'DATE_CODE_AREA',
  'EXTERNAL_LEATHER_TEXTURE', 'EXTERNAL_FABRIC_TEXTURE',
])

function missingText(dataset: string | null, model: string | null): string | null {
  if (!dataset && !model) return 'Select a dataset and model first'
  if (!dataset) return 'Select a dataset first'
  if (!model) return 'Select a model first'
  return null
}

export default function EmbeddingAnalysisPanel({ dataset, model, expectedEmbeddingCount, onResult }: Props) {
  const [analysis, setAnalysis] = useState<EmbeddingAnalysis | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [includeOutOfDataset, setIncludeOutOfDataset] = useState(false)

  const ready = !!dataset && !!model
  const missing = missingText(dataset, model)

  const run = async () => {
    if (!dataset || !model) return
    setLoading(true); setError(null); setAnalysis(null)
    try {
      const result = await getEmbeddingAnalysis(dataset, model, includeOutOfDataset)
      setAnalysis(result)
      onResult?.(result)
    } catch (e) { setError(String(e)) }
    setLoading(false)
  }

  // Compute warnings
  const warnings: string[] = []
  if (analysis) {
    if (analysis.norm_mean < 0.95 || analysis.norm_mean > 1.05) {
      warnings.push(`Norm mean is ${analysis.norm_mean} (expected ~1.0 for unit-normalized embeddings). Check for stale embeddings or normalization issues.`)
    }
    // Only warn about count mismatch when dataset-scoped (should match compatibility)
    if (analysis.dataset_scoped !== false && expectedEmbeddingCount !== undefined && expectedEmbeddingCount !== analysis.count) {
      warnings.push(`Count mismatch: compatibility reports ${expectedEmbeddingCount} embeddings, analysis found ${analysis.count}. Check for duplicate or orphaned embeddings.`)
    }
    const unexpectedRegions = Object.keys(analysis.region_counts).filter(r => !KNOWN_REGIONS.has(r))
    if (unexpectedRegions.length > 0) {
      warnings.push(`Unexpected region code(s): ${unexpectedRegions.join(', ')}. Check canonical region mapping or legacy data.`)
    }
  }

  return (
    <div className="panel">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>Embedding Analysis</h3>
        <div className="flex-row">
          <label style={{ fontSize: 11, color: 'var(--text-dim)', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={includeOutOfDataset}
              onChange={e => setIncludeOutOfDataset(e.target.checked)}
              style={{ marginRight: 4 }}
            />
            Include out-of-dataset
          </label>
          <button onClick={run} disabled={loading || !ready} style={{ marginLeft: 8 }}>
            {loading ? 'Running...' : 'Analyze'}
          </button>
        </div>
      </div>
      <p style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 4 }}>
        Diagnostics validate embedding behavior, not authentication accuracy.
        For unit-normalized embeddings, norm mean should be close to 1.0.
      </p>
      {missing && <p className="mono mt-8" style={{ color: 'var(--yellow)', fontSize: 12 }}>{missing}</p>}
      {error && <p style={{ color: 'var(--red)', fontSize: 12, marginTop: 8 }}>Error: {error}</p>}
      {ready && !analysis && !loading && !error && (
        <p className="mono mt-8" style={{ fontSize: 12 }}>Click Analyze to compute embedding statistics for {dataset} / {model}</p>
      )}
      {analysis && (
        <div className="mt-8" style={{ fontSize: 12 }}>
          {analysis.dataset_scoped !== false && (
            <p style={{ fontSize: 10, color: 'var(--text-dim)', marginBottom: 6 }}>Analysis scoped to dataset members only.</p>
          )}
          {analysis.dataset_scoped === false && (
            <p style={{ fontSize: 10, color: 'var(--yellow)', marginBottom: 6 }}>⚠ Includes embeddings outside dataset membership.</p>
          )}
          {warnings.length > 0 && (
            <div style={{ background: '#713f12', border: '1px solid var(--yellow)', borderRadius: 4, padding: 8, marginBottom: 10 }}>
              {warnings.map((w, i) => (
                <p key={i} style={{ color: 'var(--yellow)', fontSize: 11, marginBottom: i < warnings.length - 1 ? 4 : 0 }}>⚠ {w}</p>
              ))}
            </div>
          )}
          <div className="grid-2">
            <div>Embeddings: <strong>{analysis.count}</strong></div>
            <div>Dimension: <strong>{analysis.dimension}</strong></div>
            <div>Norm mean: <strong style={{ color: (analysis.norm_mean < 0.95 || analysis.norm_mean > 1.05) ? 'var(--yellow)' : undefined }}>{analysis.norm_mean}</strong></div>
            <div>Cluster separation: <strong style={{ color: analysis.cluster_separation > 0 ? 'var(--green)' : 'var(--red)' }}>{analysis.cluster_separation}</strong>
              <span style={{ fontSize: 10, color: 'var(--text-dim)', marginLeft: 4 }}>(diagnostic only)</span>
            </div>
            <div>Intra-class: <strong>{analysis.intra_class_mean}</strong></div>
            <div>Inter-class: <strong>{analysis.inter_class_mean}</strong></div>
            <div>Pairwise mean: <strong>{analysis.pairwise_mean}</strong></div>
            <div>Pairs sampled: <strong>{analysis.pairs_sampled}</strong></div>
          </div>
          <div className="mt-8">
            <span className="mono">Regions: </span>
            {Object.entries(analysis.region_counts).map(([r, c]) => (
              <span key={r} className="badge pending" style={{
                marginRight: 4,
                borderColor: KNOWN_REGIONS.has(r) ? undefined : 'var(--yellow)',
                color: KNOWN_REGIONS.has(r) ? undefined : 'var(--yellow)',
              }}>{r}: {c.total}</span>
            ))}
          </div>
          <div className="mt-8">
            <span className="mono">Labels: </span>
            {analysis.unique_labels.map(l => (
              <span key={l} className="badge pending" style={{ marginRight: 4 }}>{l}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
