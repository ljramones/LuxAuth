import type { CompleteSessionResponse } from '../api/types'

export default function SessionSummary({ result }: { result: CompleteSessionResponse }) {
  return (
    <div className="panel">
      <h3>Session Result</h3>
      <div className="flex-row mb-8">
        <span>Status:</span>
        <span className={`badge ${result.status === 'COMPLETE' ? 'complete' : 'incomplete'}`}>
          {result.status}
        </span>
      </div>
      <p className="mono mb-4">Total images: {result.total_images}</p>
      {result.missing_regions.length > 0 && (
        <div>
          <p className="mono mb-4" style={{ color: 'var(--orange)' }}>Missing regions:</p>
          {result.missing_regions.map(r => <p key={r} className="mono" style={{ paddingLeft: 12 }}>• {r}</p>)}
        </div>
      )}
      <p className="mono mt-8" style={{ color: 'var(--text-dim)', fontSize: 11 }}>
        This is a capture session, not an authentication decision.
      </p>
    </div>
  )
}
