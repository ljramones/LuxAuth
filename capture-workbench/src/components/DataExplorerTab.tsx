import { useEffect, useState } from 'react'
import {
  getOverview, getDatasets, getDatasetStats, getDatasetWarnings,
  getDatasetImages, getDatasetItems,
  type DataOverview, type DatasetRow, type DatasetStats, type DataWarning,
  type DatasetImage, type DatasetItem,
} from '../api/dataExplorerApi'

function shortId(id: string) { return id.length > 12 ? `${id.slice(0, 8)}…${id.slice(-4)}` : id }

interface Props { onOpenInDiagnostics?: (dv: string) => void }

export default function DataExplorerTab({ onOpenInDiagnostics }: Props) {
  const [overview, setOverview] = useState<DataOverview | null>(null)
  const [datasets, setDatasets] = useState<DatasetRow[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [stats, setStats] = useState<DatasetStats | null>(null)
  const [warnings, setWarnings] = useState<DataWarning[]>([])
  const [images, setImages] = useState<DatasetImage[]>([])
  const [imageTotal, setImageTotal] = useState(0)
  const [items, setItems] = useState<DatasetItem[]>([])
  const [imgFilter, setImgFilter] = useState({ split: '', region_code: '', label: '' })
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getOverview().then(setOverview).catch(e => setError(String(e)))
    getDatasets().then(setDatasets).catch(e => setError(String(e)))
  }, [])

  useEffect(() => {
    if (!selected) { setStats(null); setWarnings([]); setImages([]); setItems([]); return }
    getDatasetStats(selected).then(setStats).catch(() => {})
    getDatasetWarnings(selected).then(setWarnings).catch(() => setWarnings([]))
    getDatasetItems(selected).then(setItems).catch(() => setItems([]))
    loadImages(selected, {})
  }, [selected])

  const loadImages = (dv: string, filters: Record<string, string>) => {
    const params: Record<string, string> = { limit: '50' }
    for (const [k, v] of Object.entries(filters)) { if (v) params[k] = v }
    getDatasetImages(dv, params).then(r => { setImages(r.images); setImageTotal(r.total) }).catch(() => {})
  }

  const applyFilter = () => { if (selected) loadImages(selected, imgFilter) }

  const copySummary = () => {
    if (!stats) return
    const lines = [
      `## Data Explorer Summary — ${selected}`,
      `Status: ${stats.status} | Source: ${stats.source_type}`,
      `Splits: ${Object.entries(stats.splits).map(([s, c]) => `${s}=${c}`).join(', ')}`,
      `Labels: ${Object.entries(stats.label_counts).map(([l, c]) => `${l}=${c}`).join(', ')}`,
      `Regions: ${Object.entries(stats.region_counts).map(([r, c]) => `${r}=${c}`).join(', ')}`,
      `Embeddings: ${Object.entries(stats.embedding_counts_by_model).map(([m, c]) => `${m}=${c}`).join(', ')}`,
      `Warnings: ${warnings.length}`,
      `Items: ${items.length}`,
      '',
      '*Local data inventory only — not authentication.*',
    ]
    navigator.clipboard.writeText(lines.join('\n'))
  }

  return (
    <>
      {error && <div className="error-banner">{error}</div>}

      {/* Overview cards */}
      {overview && (
        <div className="panel">
          <h3>Global Overview</h3>
          <div className="grid-3 mt-8" style={{ fontSize: 12 }}>
            {([
              ['Datasets', overview.datasets],
              ['Reference Items', overview.reference_items],
              ['Reference Images', overview.reference_images],
              ['Embeddings', overview.embeddings],
              ['Capture Batches', overview.capture_batches],
              ['Quality PASS', overview.quality_reports_pass],
              ['Quality FAIL', overview.quality_reports_fail],
              ['Condition Records', overview.condition_metadata],
              ['Component Records', overview.component_conditions],
            ] as [string, number][]).map(([label, val]) => (
              <div key={label} style={{ background: 'var(--bg)', borderRadius: 4, padding: '8px 12px' }}>
                <div style={{ color: 'var(--text-dim)', fontSize: 10 }}>{label}</div>
                <div style={{ fontSize: 18, fontWeight: 'bold' }}>{val}</div>
              </div>
            ))}
          </div>
          {Object.keys(overview.embeddings_by_model).length > 0 && (
            <div className="mt-8" style={{ fontSize: 11 }}>
              <span className="mono">Embeddings by model: </span>
              {Object.entries(overview.embeddings_by_model).map(([m, c]) => (
                <span key={m} className="badge pending" style={{ marginRight: 4 }}>{m}: {c}</span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Dataset table */}
      <div className="panel">
        <h3>Dataset Inventory {selected && <span className="badge pass" style={{ marginLeft: 8, fontSize: 11 }}>{selected}</span>}</h3>
        {!selected && <p style={{ fontSize: 12, color: 'var(--yellow)', marginBottom: 8 }}>Click a row to inspect</p>}
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left' }}>
                <th style={{ padding: '4px 6px' }}></th>
                <th>Version</th><th>Status</th><th>Source</th>
                <th>Images</th><th>Items</th><th>Train</th><th>Val</th><th>Test</th>
                <th>Regions</th><th>Embeddings</th>
              </tr>
            </thead>
            <tbody>
              {datasets.map(ds => (
                <tr key={ds.dataset_version} onClick={() => setSelected(ds.dataset_version)}
                  style={{ cursor: 'pointer', borderBottom: '1px solid var(--border)', background: selected === ds.dataset_version ? 'rgba(76,201,240,0.15)' : undefined, borderLeft: selected === ds.dataset_version ? '3px solid var(--accent)' : '3px solid transparent' }}>
                  <td style={{ padding: '4px 6px', textAlign: 'center' }}>{selected === ds.dataset_version ? '●' : '○'}</td>
                  <td style={{ fontWeight: selected === ds.dataset_version ? 'bold' : 'normal' }}>{ds.dataset_version}</td>
                  <td><span className={`badge ${ds.status === 'active' ? 'pass' : 'pending'}`}>{ds.status}</span></td>
                  <td className="mono">{ds.source_type}</td>
                  <td>{ds.image_count}</td><td>{ds.item_count}</td>
                  <td>{ds.train_count}</td><td>{ds.validation_count}</td><td>{ds.test_count}</td>
                  <td>{ds.region_codes.length}</td>
                  <td>{Object.values(ds.embedding_counts_by_model).reduce((a, b) => a + b, 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Selected dataset detail */}
      {stats && (
        <div className="panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3>Dataset: {selected}</h3>
            <div className="flex-row">
              {onOpenInDiagnostics && <button onClick={() => onOpenInDiagnostics(selected!)}>Open in ML Diagnostics</button>}
              <button onClick={copySummary} style={{ marginLeft: 4 }}>Copy Summary</button>
            </div>
          </div>
          <div className="grid-2 mt-8" style={{ fontSize: 12 }}>
            <div><strong>Status:</strong> {stats.status}</div>
            <div><strong>Source:</strong> {stats.source_type}</div>
          </div>
          <div className="grid-3 mt-8" style={{ fontSize: 11 }}>
            <div>
              <span className="mono">Splits: </span>
              {Object.entries(stats.splits).map(([s, c]) => <span key={s} className="badge pending" style={{ marginRight: 4 }}>{s}: {c}</span>)}
            </div>
            <div>
              <span className="mono">Regions: </span>
              {Object.entries(stats.region_counts).map(([r, c]) => <span key={r} className="badge pending" style={{ marginRight: 4 }}>{r}: {c}</span>)}
            </div>
            <div>
              <span className="mono">Labels: </span>
              {Object.entries(stats.label_counts).map(([l, c]) => <span key={l} className="badge pending" style={{ marginRight: 4 }}>{l}: {c}</span>)}
            </div>
          </div>
          {Object.keys(stats.embedding_counts_by_model).length > 0 && (
            <div className="mt-8" style={{ fontSize: 11 }}>
              <span className="mono">Embeddings: </span>
              {Object.entries(stats.embedding_counts_by_model).map(([m, c]) => <span key={m} className="badge pending" style={{ marginRight: 4 }}>{m}: {c}</span>)}
            </div>
          )}
          {Object.keys(stats.condition_grades).length > 0 && (
            <div className="mt-8" style={{ fontSize: 11 }}>
              <span className="mono">Conditions: </span>
              {Object.entries(stats.condition_grades).map(([g, c]) => <span key={g} className="badge pending" style={{ marginRight: 4 }}>{g}: {c}</span>)}
            </div>
          )}
          {Object.keys(stats.component_statuses).length > 0 && (
            <div className="mt-8" style={{ fontSize: 11 }}>
              <span className="mono">Components: </span>
              {Object.entries(stats.component_statuses).map(([s, c]) => <span key={s} className="badge pending" style={{ marginRight: 4 }}>{s}: {c}</span>)}
            </div>
          )}
        </div>
      )}

      {/* Warnings */}
      {selected && (
        <div className="panel">
          <h3>Warnings ({warnings.length})</h3>
          {warnings.length === 0 && <p className="mono" style={{ fontSize: 12, color: 'var(--green)' }}>No warnings</p>}
          {warnings.map((w, i) => (
            <div key={i} style={{ padding: '6px 0', borderBottom: '1px solid var(--border)', fontSize: 12 }}>
              <span className={`badge ${w.severity === 'warning' ? 'fail' : 'pending'}`} style={{ marginRight: 8 }}>{w.severity}</span>
              <span>{w.message}</span>
              {w.affected_count > 0 && <span className="mono" style={{ marginLeft: 8, color: 'var(--text-dim)' }}>({w.affected_count} affected)</span>}
              {w.recommended_action && <p className="mono" style={{ fontSize: 10, color: 'var(--text-dim)', paddingLeft: 4, marginTop: 2 }}>{w.recommended_action}</p>}
            </div>
          ))}
        </div>
      )}

      {/* Item browser */}
      {selected && items.length > 0 && (
        <div className="panel">
          <h3>Items ({items.length})</h3>
          <div style={{ overflowX: 'auto', maxHeight: 300, overflowY: 'auto' }}>
            <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left' }}>
                  <th style={{ padding: '3px 6px' }}>ID</th><th>Label</th><th>Brand</th><th>Material</th>
                  <th>Images</th><th>Split</th><th>Condition</th><th>Repairs</th>
                </tr>
              </thead>
              <tbody>
                {items.map(it => (
                  <tr key={it.reference_item_id} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td className="mono" style={{ padding: '3px 6px' }}>{shortId(it.reference_item_id)}</td>
                    <td>{it.authenticity_status}</td>
                    <td>{it.brand}</td><td>{it.material}</td>
                    <td>{it.image_count}</td><td>{it.split}</td>
                    <td>{it.condition_grade || '—'}</td>
                    <td>{it.known_repairs ? (it.third_party_repair ? '3rd-party' : 'yes') : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Image browser */}
      {selected && (
        <div className="panel">
          <h3>Images ({imageTotal})</h3>
          <div className="flex-row mb-8" style={{ gap: 6, flexWrap: 'wrap' }}>
            <input placeholder="split" value={imgFilter.split} onChange={e => setImgFilter(f => ({ ...f, split: e.target.value }))} style={{ width: 80 }} />
            <input placeholder="region" value={imgFilter.region_code} onChange={e => setImgFilter(f => ({ ...f, region_code: e.target.value }))} style={{ width: 140 }} />
            <input placeholder="label" value={imgFilter.label} onChange={e => setImgFilter(f => ({ ...f, label: e.target.value }))} style={{ width: 140 }} />
            <button onClick={applyFilter}>Filter</button>
          </div>
          <div style={{ overflowX: 'auto', maxHeight: 300, overflowY: 'auto' }}>
            <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left' }}>
                  <th style={{ padding: '3px 6px' }}>Image ID</th><th>Item ID</th><th>Region</th>
                  <th>Split</th><th>Label</th>
                </tr>
              </thead>
              <tbody>
                {images.map(img => (
                  <tr key={img.reference_image_id} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td className="mono" style={{ padding: '3px 6px' }}>{shortId(img.reference_image_id)}</td>
                    <td className="mono">{shortId(img.reference_item_id)}</td>
                    <td>{img.region_code}</td>
                    <td>{img.split}</td>
                    <td>{img.authenticity_status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {imageTotal > images.length && <p className="mono mt-8" style={{ fontSize: 10, color: 'var(--text-dim)' }}>Showing {images.length} of {imageTotal}</p>}
        </div>
      )}

      <p style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 12 }}>
        Data Explorer is read-only local inventory. It does not modify datasets or make authentication claims.
      </p>
    </>
  )
}
