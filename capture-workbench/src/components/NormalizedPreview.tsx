import type { NormalizationResult } from '../api/types'

export default function NormalizedPreview({ result }: { result: NormalizationResult }) {
  return (
    <div style={{ fontSize: 11, padding: 6, background: 'var(--bg)', borderRadius: 4, marginTop: 4 }}>
      <span style={{ color: 'var(--green)' }}>✓ Normalized</span>
      <div className="mono" style={{ marginTop: 2, wordBreak: 'break-all' }}>
        {result.preprocessing_version}
      </div>
    </div>
  )
}
