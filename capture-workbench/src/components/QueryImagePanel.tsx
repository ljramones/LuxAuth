import { useState, useRef } from 'react'
import { queryImage, type QueryImageResult, type QueryNeighbor } from '../api/queryImageApi'

const COLORS: Record<string, string> = {
  CONFIRMED_AUTHENTIC: '#4ade80',
  CONFIRMED_COUNTERFEIT: '#f87171',
  PUBLIC_DATASET_CLASS: '#4cc9f0',
  QUERY_IMAGE: '#fbbf24',
}

function shortId(id: string): string {
  return id.length > 12 ? `${id.slice(0, 8)}…${id.slice(-4)}` : id
}

function shortLabel(label: string): string {
  if (label.includes('AUTHENTIC')) return 'auth'
  if (label.includes('COUNTERFEIT')) return 'counter'
  if (label.includes('PUBLIC')) return 'public'
  if (label === 'QUERY_IMAGE') return 'QUERY'
  return label.slice(0, 12)
}

interface Interpretation {
  band: string
  color: string
  message: string
  top1Sim: number
  top1Label: string
  meanSim: number
  gap: number | null
  labelDist: Record<string, number>
  lowSimWarning: string | null
}

function interpret(neighbors: QueryNeighbor[]): Interpretation | null {
  if (neighbors.length === 0) return null

  const top1 = neighbors[0]
  const top1Sim = top1.similarity
  const top1Label = top1.label
  const meanSim = neighbors.reduce((s, n) => s + n.similarity, 0) / neighbors.length
  const gap = neighbors.length >= 2 ? top1.similarity - neighbors[1].similarity : null

  const labelDist: Record<string, number> = {}
  for (const n of neighbors) {
    const l = shortLabel(n.label)
    labelDist[l] = (labelDist[l] || 0) + 1
  }

  let band: string; let color: string; let message: string
  if (top1Sim >= 0.85) {
    band = 'HIGH'; color = 'var(--green)'
    message = 'High similarity to selected reference dataset'
  } else if (top1Sim >= 0.65) {
    band = 'MODERATE'; color = 'var(--yellow)'
    message = 'Moderate similarity — inspect neighbors carefully'
  } else if (top1Sim >= 0.50) {
    band = 'WEAK'; color = 'var(--orange)'
    message = 'Weak similarity — possible mismatch or insufficient reference coverage'
  } else {
    band = 'VERY LOW'; color = 'var(--red)'
    message = 'Very low similarity — likely out-of-distribution for selected dataset/model'
  }

  // Check for misleading label consensus at low similarity
  const dominantCount = Math.max(...Object.values(labelDist))
  let lowSimWarning: string | null = null
  if (top1Sim < 0.50 && dominantCount === neighbors.length) {
    const dominantLabel = Object.entries(labelDist).find(([, c]) => c === dominantCount)?.[0] || '?'
    lowSimWarning = `All ${neighbors.length} neighbors share label "${dominantLabel}", but similarity is low (${top1Sim.toFixed(3)}). Do not interpret this as class evidence.`
  }

  return { band, color, message, top1Sim, top1Label, meanSim, gap, labelDist, lowSimWarning }
}

interface Props {
  dataset: string | null
  model: string | null
  isCompatible: boolean
  onNoteSummary?: (text: string) => void
}

export default function QueryImagePanel({ dataset, model, isCompatible, onNoteSummary }: Props) {
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [result, setResult] = useState<QueryImageResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [k, setK] = useState(5)
  const [includeProj, setIncludeProj] = useState(true)
  const [regionFilter, setRegionFilter] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const ready = !!dataset && !!model && isCompatible && !!file

  const handleFile = (f: File) => {
    setFile(f)
    setPreview(URL.createObjectURL(f))
    setResult(null)
    setError(null)
  }

  const run = async () => {
    if (!dataset || !model || !file) return
    setLoading(true); setError(null); setResult(null)
    try {
      setResult(await queryImage(file, dataset, model, k, includeProj, false, regionFilter))
    } catch (e) { setError(String(e)) }
    setLoading(false)
  }

  const interp = result ? interpret(result.neighbors) : null

  const addToNotes = () => {
    if (!result || !onNoteSummary) return
    const lines = [
      `Query image result — ${new Date().toISOString().slice(0, 19)} UTC`,
      `Dataset: ${result.dataset_version}`,
      `Model: ${result.model_version}`,
    ]
    if (result.quality) {
      lines.push(`Quality: ${result.quality.quality_status} (sharpness=${result.quality.sharpness_score}, exposure=${result.quality.exposure_score}, glare=${result.quality.glare_score})`)
    }
    if (result.embedding) {
      lines.push(`Embedding: dim=${result.embedding.dimension}, norm=${result.embedding.norm}`)
    }
    lines.push(`Search scope: ${result.search_scope}${result.query_region_code ? ` (${result.query_region_code})` : ''}`)
    if (interp) {
      lines.push(`Interpretation: ${interp.band} — ${interp.message}`)
      lines.push(`Top-1: sim=${interp.top1Sim.toFixed(3)}, label=${shortLabel(interp.top1Label)}`)
      lines.push(`Mean top-${result.neighbors.length}: ${interp.meanSim.toFixed(3)}`)
      if (interp.gap !== null) lines.push(`Gap (rank 1 vs 2): ${interp.gap.toFixed(4)}`)
      lines.push(`Label distribution: ${Object.entries(interp.labelDist).map(([l, c]) => `${l}=${c}`).join(', ')}`)
      if (interp.lowSimWarning) lines.push(`WARNING: ${interp.lowSimWarning}`)
    }
    lines.push('Reminder: diagnostic only, not authentication.')
    onNoteSummary(lines.join('\n'))
  }

  // Projection rendering
  const proj = result?.projection
  const margin = 20; const size = 360
  let sx = (_v: number) => 0; let sy = (_v: number) => 0
  if (proj) {
    const allPts = [...proj.reference_points.map(p => [p.x, p.y]), [proj.query_point.x, proj.query_point.y]]
    const xs = allPts.map(p => p[0]); const ys = allPts.map(p => p[1])
    const xMin = Math.min(...xs); const xMax = Math.max(...xs)
    const yMin = Math.min(...ys); const yMax = Math.max(...ys)
    sx = (v: number) => margin + ((v - xMin) / (xMax - xMin || 1)) * (size - 2 * margin)
    sy = (v: number) => margin + ((v - yMin) / (yMax - yMin || 1)) * (size - 2 * margin)
  }

  return (
    <div className="panel" style={{ borderColor: 'var(--accent)', borderWidth: 1 }}>
      <h3>Query Image Nearest Neighbors <span className="badge pending" style={{ fontSize: 10, marginLeft: 6 }}>diagnostic query</span></h3>
      <p style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 4 }}>
        Upload a single image to see how the embedding space responds. Diagnostic only — does not authenticate or add to any dataset.
      </p>

      {/* Controls */}
      <div className="flex-row mt-8" style={{ flexWrap: 'wrap', gap: 8 }}>
        <div
          className="upload-zone"
          style={{ width: 120, height: 80, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11 }}
          onClick={() => inputRef.current?.click()}
        >
          {preview ? <img src={preview} style={{ maxWidth: 110, maxHeight: 70, borderRadius: 4 }} /> : '+ Upload image'}
          <input ref={inputRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])} />
        </div>
        <div>
          <label style={{ fontSize: 11 }}>K</label>
          <input type="number" value={k} onChange={e => setK(Number(e.target.value) || 5)} min={1} max={20} style={{ width: 50 }} />
        </div>
        <div>
          <label style={{ fontSize: 11 }}>Region</label>
          <select value={regionFilter} onChange={e => setRegionFilter(e.target.value)} style={{ width: 160 }}>
            <option value="">All regions</option>
            {(result?.available_region_codes || []).map(r => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
        <label style={{ fontSize: 11, cursor: 'pointer' }}>
          <input type="checkbox" checked={includeProj} onChange={e => setIncludeProj(e.target.checked)} /> Projection
        </label>
        <button onClick={run} disabled={!ready || loading}>
          {loading ? 'Running…' : 'Run Query'}
        </button>
        {result && onNoteSummary && (
          <button onClick={addToNotes} style={{ marginLeft: 4 }}>Add to Notes</button>
        )}
      </div>

      {!dataset && <p className="mono mt-8" style={{ color: 'var(--yellow)', fontSize: 12 }}>Select a dataset first</p>}
      {dataset && !isCompatible && <p className="mono mt-8" style={{ color: 'var(--yellow)', fontSize: 12 }}>Select a model with embeddings</p>}
      {dataset && isCompatible && !file && <p className="mono mt-8" style={{ color: 'var(--text-dim)', fontSize: 12 }}>Upload an image to query</p>}
      {error && <p style={{ color: 'var(--red)', fontSize: 12, marginTop: 8 }}>Error: {error}</p>}

      {/* Warnings */}
      {result?.warnings && result.warnings.length > 0 && (
        <div style={{ marginTop: 8 }}>
          {result.warnings.map((w, i) => (
            <p key={i} style={{ fontSize: 11, color: 'var(--yellow)' }}>⚠ {w}</p>
          ))}
        </div>
      )}

      {/* Quality */}
      {result?.quality && (
        <div className="mt-8" style={{ fontSize: 12 }}>
          <strong>Quality:</strong>{' '}
          <span className={`badge ${result.quality.quality_status === 'PASS' ? 'pass' : 'fail'}`}>{result.quality.quality_status}</span>
          <span className="mono" style={{ marginLeft: 8 }}>
            sharp={result.quality.sharpness_score} exp={result.quality.exposure_score} glare={result.quality.glare_score}
          </span>
          {result.quality.issues.length > 0 && (
            <span style={{ color: 'var(--red)', marginLeft: 8 }}>{result.quality.issues.join(', ')}</span>
          )}
        </div>
      )}

      {/* Embedding */}
      {result?.embedding && (
        <div style={{ fontSize: 12, marginTop: 4 }}>
          <strong>Embedding:</strong> <span className="mono">dim={result.embedding.dimension} norm={result.embedding.norm}</span>
        </div>
      )}

      {/* Interpretation */}
      {interp && (
        <div className="mt-8" style={{ background: 'var(--bg)', border: `1px solid ${interp.color}`, borderRadius: 4, padding: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
            <span className="badge" style={{ background: interp.color, color: '#000', fontWeight: 'bold' }}>{interp.band}</span>
            <span style={{ fontSize: 12 }}>{interp.message}</span>
          </div>
          <div className="grid-2" style={{ fontSize: 11 }}>
            <div>Top-1 similarity: <strong>{interp.top1Sim.toFixed(3)}</strong></div>
            <div>Top-1 label: <strong>{shortLabel(interp.top1Label)}</strong></div>
            <div>Mean top-{result!.neighbors.length}: <strong>{interp.meanSim.toFixed(3)}</strong></div>
            {interp.gap !== null && <div>Rank 1→2 gap: <strong>{interp.gap.toFixed(4)}</strong></div>}
          </div>
          <div style={{ fontSize: 11, marginTop: 6 }}>
            <span>Label distribution: </span>
            {Object.entries(interp.labelDist).map(([l, c]) => (
              <span key={l} className="badge pending" style={{ marginRight: 4 }}>{l}: {c}</span>
            ))}
          </div>
          {/* Search scope */}
          {result && (
            <div style={{ fontSize: 11, marginTop: 6, color: 'var(--text-dim)' }}>
              Search scope: <strong>{result.search_scope === 'region_filtered' ? `region-filtered (${result.query_region_code})` : 'all regions'}</strong>
            </div>
          )}
          {/* Mixed-region warning for all-region search */}
          {result && result.search_scope === 'all_regions' && result.neighbors.length >= 2 && (() => {
            const neighborRegions = new Set(result.neighbors.map(n => n.region_code))
            return neighborRegions.size > 1 ? (
              <p style={{ fontSize: 11, color: 'var(--yellow)', marginTop: 6 }}>
                ⚠ All-region search returned neighbors from {neighborRegions.size} region types. Consider selecting a query region for a like-for-like comparison.
              </p>
            ) : null
          })()}
          {interp.lowSimWarning && (
            <p style={{ fontSize: 11, color: 'var(--red)', marginTop: 6 }}>⚠ {interp.lowSimWarning}</p>
          )}
          <p style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 6 }}>
            This is diagnostic only and not an authentication decision.
          </p>
        </div>
      )}

      {/* Neighbors */}
      {result && result.neighbors.length > 0 && (
        <div className="mt-8">
          <strong style={{ fontSize: 12 }}>Top-{result.neighbors.length} Neighbors</strong>
          <p style={{ fontSize: 10, color: 'var(--text-dim)' }}>Similarity in embedding space, not an authentication verdict.</p>
          <div style={{ marginTop: 4 }}>
            {result.neighbors.map(n => (
              <div key={n.rank} style={{ fontSize: 11, padding: '3px 0', borderBottom: '1px solid var(--border)', display: 'grid', gridTemplateColumns: '24px 70px 80px 1fr 80px', gap: 4 }}>
                <span className="mono">#{n.rank}</span>
                <span className="mono">sim={n.similarity.toFixed(3)}</span>
                <span>{shortLabel(n.label)}</span>
                <span className="mono" style={{ color: 'var(--text-dim)' }}>{n.region_code}</span>
                <span className="mono" style={{ color: 'var(--text-dim)' }}>{shortId(n.reference_image_id)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Projection */}
      {proj && (
        <div className="mt-8">
          <strong style={{ fontSize: 12 }}>Query Projection</strong>
          <svg width={size} height={size} style={{ background: 'var(--bg)', borderRadius: 4, marginTop: 4 }}>
            {proj.reference_points.map((p, i) => (
              <circle key={i} cx={sx(p.x)} cy={sy(p.y)} r={3}
                fill={COLORS[p.label] || '#888'} opacity={0.5}>
                <title>{`${p.label}\n${p.region_code}\n${p.split}`}</title>
              </circle>
            ))}
            <circle cx={sx(proj.query_point.x)} cy={sy(proj.query_point.y)} r={7}
              fill={COLORS.QUERY_IMAGE} stroke="#fff" strokeWidth={2} opacity={0.95}>
              <title>QUERY IMAGE</title>
            </circle>
            <text x={sx(proj.query_point.x) + 10} y={sy(proj.query_point.y) + 4}
              fill={COLORS.QUERY_IMAGE} fontSize={10} fontWeight="bold">QUERY</text>
          </svg>
          <div className="flex-row mt-8" style={{ fontSize: 10 }}>
            <span style={{ marginRight: 12 }}>
              <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: COLORS.QUERY_IMAGE, marginRight: 4 }} />
              Query
            </span>
            {Object.entries(COLORS).filter(([l]) => l !== 'QUERY_IMAGE').map(([label, color]) => (
              <span key={label} style={{ marginRight: 12 }}>
                <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: color, marginRight: 4 }} />
                {label}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
