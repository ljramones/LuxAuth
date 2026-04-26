import { useState } from 'react'
import { getNeighbors, type NeighborResult } from '../api/mlDiagnosticsApi'

interface Props { dataset: string | null; model: string | null; onResult?: (r: NeighborResult) => void }

function missingText(dataset: string | null, model: string | null): string | null {
  if (!dataset && !model) return 'Select a dataset and model first'
  if (!dataset) return 'Select a dataset first'
  if (!model) return 'Select a model first'
  return null
}

function shortLabel(label: string): string {
  if (label.includes('AUTHENTIC')) return 'auth'
  if (label.includes('COUNTERFEIT')) return 'counter'
  if (label.includes('PUBLIC')) return 'public'
  return label.slice(0, 12)
}

export default function NeighborsPanel({ dataset, model, onResult }: Props) {
  const [result, setResult] = useState<NeighborResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const ready = !!dataset && !!model
  const missing = missingText(dataset, model)

  const run = async () => {
    if (!dataset || !model) return
    setLoading(true); setError(null); setResult(null)
    try {
      const r = await getNeighbors(dataset, model)
      setResult(r)
      onResult?.(r)
    } catch (e) { setError(String(e)) }
    setLoading(false)
  }

  return (
    <div className="panel">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>Nearest Neighbors</h3>
        <button onClick={run} disabled={loading || !ready}>{loading ? 'Running...' : 'Inspect'}</button>
      </div>
      <p style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 4 }}>
        Shows whether embeddings retrieve expected nearby references. Diagnostic only.
      </p>
      {missing && <p className="mono mt-8" style={{ color: 'var(--yellow)', fontSize: 12 }}>{missing}</p>}
      {error && <p style={{ color: 'var(--red)', fontSize: 12, marginTop: 8 }}>Error: {error}</p>}
      {ready && !result && !loading && !error && (
        <p className="mono mt-8" style={{ fontSize: 12 }}>Click Inspect to compute nearest neighbors for {dataset} / {model}</p>
      )}
      {result && (
        <div className="mt-8" style={{ fontSize: 12 }}>
          <div className="flex-row mb-8">
            <span>NN Agreement: <strong>{result.nn_agreement}/{result.total}</strong></span>
            <span className={`badge ${result.nn_agreement_rate > 0.8 ? 'pass' : result.nn_agreement_rate > 0.5 ? 'pending' : 'fail'}`} style={{ marginLeft: 8 }}>
              {(result.nn_agreement_rate * 100).toFixed(1)}%
            </span>
            <span style={{ marginLeft: 12, fontSize: 10, color: 'var(--text-dim)' }}>
              (nearest neighbor has same label as query)
            </span>
          </div>
          {result.items.length === 0 && (
            <p className="mono" style={{ color: 'var(--orange)' }}>No test-split items found for this dataset/model pair.</p>
          )}
          {result.items.length > 0 && (
            <>
              {/* Column headers */}
              <div style={{ display: 'grid', gridTemplateColumns: '20px 1fr 1fr 2fr', gap: 4, padding: '4px 0', borderBottom: '1px solid var(--border)', fontSize: 10, color: 'var(--text-dim)' }}>
                <span></span>
                <span>Region</span>
                <span>Expected label</span>
                <span>Top neighbors (rank · similarity · label · match)</span>
              </div>
              <div style={{ maxHeight: 400, overflowY: 'auto' }}>
                {result.items.map((item, i) => (
                  <div key={i} style={{ display: 'grid', gridTemplateColumns: '20px 1fr 1fr 2fr', gap: 4, padding: '6px 0', borderBottom: '1px solid var(--border)', alignItems: 'start' }}>
                    <span className={`status-dot ${item.nn_agrees ? 'green' : 'red'}`} style={{ marginTop: 2 }} />
                    <span className="mono" style={{ fontSize: 11 }}>{item.region_code}</span>
                    <span style={{ fontSize: 11 }}>{shortLabel(item.expected_label)}</span>
                    <div>
                      {item.neighbors.slice(0, 3).map((n, j) => {
                        const match = n.label === item.expected_label
                        return (
                          <div key={j} style={{ fontSize: 11, marginBottom: 2 }}>
                            <span style={{ color: 'var(--text-dim)', width: 16, display: 'inline-block' }}>#{j + 1}</span>
                            <span style={{ fontFamily: 'monospace' }}>sim={n.similarity.toFixed(3)}</span>
                            <span style={{ marginLeft: 6 }}>{shortLabel(n.label)}</span>
                            <span style={{ marginLeft: 6, color: match ? 'var(--green)' : 'var(--red)' }}>
                              {match ? '✓ match' : '✕ mismatch'}
                            </span>
                          </div>
                        )
                      })}
                      {item.neighbors.length === 0 && (
                        <span style={{ color: 'var(--text-dim)', fontSize: 11 }}>No neighbors in search split for this region</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
