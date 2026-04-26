import { useEffect, useState } from 'react'
import { listEvaluations, type EvaluationRun } from '../api/mlDiagnosticsApi'

export default function EvaluationsPanel() {
  const [evals, setEvals] = useState<EvaluationRun[]>([])

  useEffect(() => { listEvaluations().then(setEvals).catch(() => {}) }, [])

  return (
    <div className="panel">
      <h3>Evaluation Runs</h3>
      <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left' }}>
            <th style={{ padding: '4px 8px' }}>Name</th>
            <th>Model</th>
            <th>Dataset</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {evals.map(e => (
            <tr key={e.id} style={{ borderBottom: '1px solid var(--border)' }}>
              <td style={{ padding: '4px 8px', fontSize: 11 }}>{e.evaluation_name}</td>
              <td className="mono">{e.embedding_model_version}</td>
              <td className="mono">{e.reference_dataset_version}</td>
              <td><span className={`badge ${e.status === 'COMPLETED' ? 'pass' : 'pending'}`}>{e.status}</span></td>
            </tr>
          ))}
          {evals.length === 0 && <tr><td colSpan={4} style={{ padding: 8, color: 'var(--text-dim)' }}>No evaluations found</td></tr>}
        </tbody>
      </table>
    </div>
  )
}
