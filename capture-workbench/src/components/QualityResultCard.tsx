import type { QualityReport } from '../api/types'

function ScoreBar({ value, label }: { value: number; label: string }) {
  const color = value > 0.7 ? 'var(--green)' : value > 0.4 ? 'var(--yellow)' : 'var(--red)'
  return (
    <div className="mb-4">
      <div className="flex-row">
        <span style={{ fontSize: 11, width: 70 }}>{label}</span>
        <span className="mono" style={{ width: 40, textAlign: 'right' }}>{value.toFixed(2)}</span>
      </div>
      <div className="score-bar"><div className="fill" style={{ width: `${value * 100}%`, background: color }} /></div>
    </div>
  )
}

export default function QualityResultCard({ report }: { report: QualityReport }) {
  return (
    <div style={{ fontSize: 12, padding: 8, background: 'var(--bg)', borderRadius: 4, marginTop: 4 }}>
      <div className="flex-row mb-4">
        <span>Quality:</span>
        <span className={`badge ${report.quality_status === 'PASS' ? 'pass' : 'fail'}`}>{report.quality_status}</span>
      </div>
      <ScoreBar value={report.sharpness_score} label="Sharpness" />
      <ScoreBar value={report.exposure_score} label="Exposure" />
      <ScoreBar value={1 - report.glare_score} label="Glare-free" />
      {report.issues.length > 0 && (
        <div className="mono" style={{ color: 'var(--red)', marginTop: 4 }}>
          {report.issues.join(', ')}
        </div>
      )}
    </div>
  )
}
