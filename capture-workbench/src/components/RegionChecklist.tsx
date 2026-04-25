import type { RegionStatus } from '../api/types'

interface Props {
  regions: RegionStatus[]
  onRefresh: () => void
}

export default function RegionChecklist({ regions, onRefresh }: Props) {
  return (
    <div className="panel">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>Region Completeness</h3>
        <button onClick={onRefresh}>Refresh</button>
      </div>
      <div className="mt-8">
        {regions.map(r => (
          <div key={r.region_code} className="flex-row mb-4" style={{ padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
            <span className={`status-dot ${r.satisfied ? 'green' : 'red'}`} />
            <span style={{ fontSize: 13, flex: 1 }}>{r.region_code}</span>
            <span className="mono">{r.uploaded}/{r.required}</span>
            <span className={`badge ${r.satisfied ? 'pass' : 'fail'}`} style={{ marginLeft: 8 }}>
              {r.satisfied ? 'OK' : 'NEED'}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
