import { useState } from 'react'
import { getProjections, type ProjectionPoint } from '../api/mlDiagnosticsApi'

interface Props { dataset: string | null; model: string | null; onPointSelected?: (p: ProjectionPoint | null) => void }

const COLORS: Record<string, string> = {
  CONFIRMED_AUTHENTIC: '#4ade80',
  CONFIRMED_COUNTERFEIT: '#f87171',
  PUBLIC_DATASET_CLASS: '#4cc9f0',
}

function missingText(dataset: string | null, model: string | null): string | null {
  if (!dataset && !model) return 'Select a dataset and model first'
  if (!dataset) return 'Select a dataset first'
  if (!model) return 'Select a model first'
  return null
}

function shortId(id: string): string {
  return id.length > 12 ? `${id.slice(0, 8)}…${id.slice(-4)}` : id
}

export default function ProjectionPanel({ dataset, model, onPointSelected }: Props) {
  const [points, setPoints] = useState<ProjectionPoint[]>([])
  const [loading, setLoading] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null)

  const ready = !!dataset && !!model
  const missing = missingText(dataset, model)

  const run = async () => {
    if (!dataset || !model) return
    setLoading(true); setError(null); setLoaded(false); setSelectedIdx(null)
    try {
      const data = await getProjections(dataset, model)
      setPoints(data)
      setLoaded(true)
    } catch (e) { setError(String(e)) }
    setLoading(false)
  }

  const margin = 24
  const size = 420
  const xs = points.map(p => p.x)
  const ys = points.map(p => p.y)
  const xMin = Math.min(...xs, 0); const xMax = Math.max(...xs, 1)
  const yMin = Math.min(...ys, 0); const yMax = Math.max(...ys, 1)
  const sx = (v: number) => margin + ((v - xMin) / (xMax - xMin || 1)) * (size - 2 * margin)
  const sy = (v: number) => margin + ((v - yMin) / (yMax - yMin || 1)) * (size - 2 * margin)

  const selectedPoint = selectedIdx !== null ? points[selectedIdx] : null

  // Summary stats
  const uniqueLabels = [...new Set(points.map(p => p.label))]
  const uniqueSplits = [...new Set(points.map(p => p.split))]
  const uniqueRegions = [...new Set(points.map(p => p.region_code))]

  return (
    <div className="panel">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>PCA Projection</h3>
        <button onClick={run} disabled={loading || !ready}>{loading ? 'Loading...' : 'Load'}</button>
      </div>
      <p style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 4 }}>
        PCA compresses embeddings to 2D for visualization. Useful for spotting clusters and outliers, but not an authentication score.
      </p>
      {missing && <p className="mono mt-8" style={{ color: 'var(--yellow)', fontSize: 12 }}>{missing}</p>}
      {error && <p style={{ color: 'var(--red)', fontSize: 12, marginTop: 8 }}>Error: {error}</p>}
      {ready && !loaded && !loading && !error && (
        <p className="mono mt-8" style={{ fontSize: 12 }}>Click Load to generate PCA projection for {dataset} / {model}</p>
      )}
      {loaded && points.length === 0 && (
        <p className="mono mt-8" style={{ color: 'var(--orange)', fontSize: 12 }}>Projection generated but no points returned.</p>
      )}
      {points.length > 0 && (
        <div className="mt-8" style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          {/* Chart */}
          <div>
            <svg
              width={size} height={size}
              style={{ background: 'var(--bg)', borderRadius: 4, cursor: 'crosshair' }}
            >
              {points.map((p, i) => {
                const isHovered = hoveredIdx === i
                const isSelected = selectedIdx === i
                const r = isSelected ? 6 : isHovered ? 5 : 3
                return (
                  <circle
                    key={i}
                    cx={sx(p.x)} cy={sy(p.y)} r={r}
                    fill={COLORS[p.label] || '#888'}
                    opacity={isSelected ? 1 : isHovered ? 0.9 : 0.6}
                    stroke={isSelected ? '#fff' : isHovered ? '#fff' : 'none'}
                    strokeWidth={isSelected ? 2 : isHovered ? 1 : 0}
                    style={{ cursor: 'pointer', transition: 'r 0.1s, opacity 0.1s' }}
                    onMouseEnter={() => setHoveredIdx(i)}
                    onMouseLeave={() => setHoveredIdx(null)}
                    onClick={() => {
                      const next = i === selectedIdx ? null : i
                      setSelectedIdx(next)
                      onPointSelected?.(next !== null ? points[next] : null)
                    }}
                  />
                )
              })}
            </svg>

            {/* Legend */}
            <div className="flex-row mt-8" style={{ fontSize: 11 }}>
              {Object.entries(COLORS).filter(([label]) => uniqueLabels.includes(label)).map(([label, color]) => (
                <span key={label} style={{ marginRight: 12 }}>
                  <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: color, marginRight: 4 }} />
                  {label}
                </span>
              ))}
            </div>

            {/* Summary */}
            <div className="mono mt-8" style={{ fontSize: 11, color: 'var(--text-dim)' }}>
              {points.length} points · {uniqueLabels.length} label(s) · {uniqueRegions.length} region(s) · {uniqueSplits.length} split(s)
            </div>
          </div>

          {/* Hover tooltip / Selection detail */}
          <div style={{ minWidth: 220, fontSize: 12 }}>
            {/* Hover info */}
            {hoveredIdx !== null && selectedIdx === null && (() => {
              const p = points[hoveredIdx]
              return (
                <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 4, padding: 10 }}>
                  <p style={{ fontWeight: 'bold', marginBottom: 4, color: COLORS[p.label] || 'var(--text)' }}>{p.label}</p>
                  <table style={{ fontSize: 11 }}>
                    <tbody>
                      <tr><td style={{ color: 'var(--text-dim)', paddingRight: 8 }}>Region</td><td>{p.region_code}</td></tr>
                      <tr><td style={{ color: 'var(--text-dim)', paddingRight: 8 }}>Split</td><td>{p.split}</td></tr>
                      <tr><td style={{ color: 'var(--text-dim)', paddingRight: 8 }}>ID</td><td className="mono">{shortId(p.reference_image_id)}</td></tr>
                      <tr><td style={{ color: 'var(--text-dim)', paddingRight: 8 }}>x</td><td className="mono">{p.x.toFixed(3)}</td></tr>
                      <tr><td style={{ color: 'var(--text-dim)', paddingRight: 8 }}>y</td><td className="mono">{p.y.toFixed(3)}</td></tr>
                    </tbody>
                  </table>
                </div>
              )
            })()}

            {/* Selected detail */}
            {selectedPoint && (
              <div style={{ background: 'var(--surface)', border: '1px solid var(--accent)', borderRadius: 4, padding: 10 }}>
                <p style={{ fontWeight: 'bold', marginBottom: 6, color: COLORS[selectedPoint.label] || 'var(--text)' }}>
                  Selected Point
                </p>
                <table style={{ fontSize: 11, width: '100%' }}>
                  <tbody>
                    <tr><td style={{ color: 'var(--text-dim)', paddingRight: 8 }}>Label</td><td>{selectedPoint.label}</td></tr>
                    <tr><td style={{ color: 'var(--text-dim)', paddingRight: 8 }}>Region</td><td>{selectedPoint.region_code}</td></tr>
                    <tr><td style={{ color: 'var(--text-dim)', paddingRight: 8 }}>Split</td><td>{selectedPoint.split}</td></tr>
                    <tr><td style={{ color: 'var(--text-dim)', paddingRight: 8 }}>ID</td><td className="mono" style={{ wordBreak: 'break-all' }}>{selectedPoint.reference_image_id}</td></tr>
                    <tr><td style={{ color: 'var(--text-dim)', paddingRight: 8 }}>x</td><td className="mono">{selectedPoint.x.toFixed(6)}</td></tr>
                    <tr><td style={{ color: 'var(--text-dim)', paddingRight: 8 }}>y</td><td className="mono">{selectedPoint.y.toFixed(6)}</td></tr>
                    {dataset && <tr><td style={{ color: 'var(--text-dim)', paddingRight: 8 }}>Dataset</td><td className="mono">{dataset}</td></tr>}
                    {model && <tr><td style={{ color: 'var(--text-dim)', paddingRight: 8 }}>Model</td><td className="mono">{model}</td></tr>}
                  </tbody>
                </table>
                <p style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 8 }}>
                  Spatial distance is PCA-compressed and should not be treated as authentication confidence.
                </p>
                <button
                  onClick={() => setSelectedIdx(null)}
                  style={{ marginTop: 8, fontSize: 11 }}
                >
                  Deselect
                </button>
              </div>
            )}

            {/* Empty state */}
            {hoveredIdx === null && selectedIdx === null && loaded && (
              <p className="mono" style={{ fontSize: 11, color: 'var(--text-dim)' }}>
                Hover over a point for quick info.<br />
                Click a point to inspect details.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
