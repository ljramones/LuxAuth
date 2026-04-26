import { useEffect, useState } from 'react'
import { listDatasets, type DatasetSummary } from '../api/mlDiagnosticsApi'

const SOURCE_BADGES: Record<string, { label: string; color: string }> = {
  public_external: { label: 'Public external — texture diagnostics only', color: 'var(--yellow)' },
  synthetic: { label: 'Synthetic — pipeline testing', color: 'var(--text-dim)' },
  lab_curated: { label: 'Lab curated', color: 'var(--accent)' },
}

interface Props { onSelect: (ds: DatasetSummary) => void; selected: string | null }

export default function DatasetsPanel({ onSelect, selected }: Props) {
  const [datasets, setDatasets] = useState<DatasetSummary[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => { listDatasets().then(setDatasets).catch(e => setError(String(e))) }, [])

  return (
    <div className="panel">
      <h3>Datasets {selected && <span className="badge pass" style={{ marginLeft: 8, fontSize: 11 }}>{selected}</span>}</h3>
      {!selected && <p style={{ fontSize: 12, color: 'var(--yellow)', marginBottom: 8 }}>👆 Click a dataset row to select it</p>}
      {error && <p style={{ color: 'var(--red)', fontSize: 12 }}>{error}</p>}
      <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left' }}>
            <th style={{ padding: '4px 8px' }}></th>
            <th style={{ padding: '4px 8px' }}>Version</th>
            <th>Status</th>
            <th>Source</th>
            <th>Images</th>
            <th>Train</th>
            <th>Val</th>
            <th>Test</th>
          </tr>
        </thead>
        <tbody>
          {datasets.map(ds => {
            const isSelected = selected === ds.dataset_version
            return (
              <tr
                key={ds.dataset_version}
                onClick={() => onSelect(ds)}
                style={{
                  cursor: 'pointer',
                  borderBottom: '1px solid var(--border)',
                  background: isSelected ? 'rgba(76, 201, 240, 0.15)' : undefined,
                  borderLeft: isSelected ? '3px solid var(--accent)' : '3px solid transparent',
                }}
              >
                <td style={{ padding: '4px 8px', textAlign: 'center' }}>
                  {isSelected ? '●' : '○'}
                </td>
                <td style={{ padding: '4px 8px', fontWeight: isSelected ? 'bold' : 'normal' }}>{ds.dataset_version}</td>
                <td><span className={`badge ${ds.status === 'active' ? 'pass' : 'pending'}`}>{ds.status}</span></td>
                <td className="mono">{ds.source_type}</td>
                <td>{ds.image_count}</td>
                <td>{ds.train_count}</td>
                <td>{ds.validation_count}</td>
                <td>{ds.test_count}</td>
              </tr>
            )
          })}
          {datasets.length === 0 && !error && (
            <tr><td colSpan={8} style={{ padding: 12, color: 'var(--text-dim)' }}>No datasets found. Ingest data first.</td></tr>
          )}
        </tbody>
      </table>
      {selected && datasets.find(d => d.dataset_version === selected)?.source_type && (
        (() => {
          const ds = datasets.find(d => d.dataset_version === selected)!
          const badge = SOURCE_BADGES[ds.source_type]
          return badge ? (
            <p style={{ fontSize: 11, color: badge.color, marginTop: 8 }}>⚠ {badge.label}</p>
          ) : ds.dataset_version.startsWith('smoke_') ? (
            <p style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 8 }}>Smoke dataset — workflow validation only.</p>
          ) : null
        })()
      )}
    </div>
  )
}
