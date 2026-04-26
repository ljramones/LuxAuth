import { useState, useEffect, useCallback } from 'react'
import type { EmbeddingAnalysis, NeighborResult, ProjectionPoint } from '../api/mlDiagnosticsApi'

interface Props {
  dataset: string | null
  model: string | null
  embeddingAnalysis: EmbeddingAnalysis | null
  neighborResult: NeighborResult | null
  selectedPoint: ProjectionPoint | null
  appendToSummary?: string | null
  onAppendConsumed?: () => void
}

interface Notes {
  summary: string
  pca: string
  neighbors: string
  clusters: string
  dataIssue: string
  modelIssue: string
  followUp: string
}

const EMPTY: Notes = { summary: '', pca: '', neighbors: '', clusters: '', dataIssue: '', modelIssue: '', followUp: '' }

function storageKey(dataset: string, model: string): string {
  return `diagnostics_notes:${dataset}:${model}`
}

function shortId(id: string): string {
  return id.length > 12 ? `${id.slice(0, 8)}…${id.slice(-4)}` : id
}

export default function DiagnosticsNotesPanel({ dataset, model, embeddingAnalysis, neighborResult, selectedPoint, appendToSummary, onAppendConsumed }: Props) {
  const [notes, setNotes] = useState<Notes>(EMPTY)
  const [saved, setSaved] = useState(true)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!dataset || !model) { setNotes(EMPTY); return }
    const raw = localStorage.getItem(storageKey(dataset, model))
    if (raw) {
      try { setNotes({ ...EMPTY, ...JSON.parse(raw) }) } catch { setNotes(EMPTY) }
    } else {
      setNotes(EMPTY)
    }
    setSaved(true)
  }, [dataset, model])

  useEffect(() => {
    if (!dataset || !model || saved) return
    const timer = setTimeout(() => {
      localStorage.setItem(storageKey(dataset, model), JSON.stringify(notes))
      setSaved(true)
    }, 500)
    return () => clearTimeout(timer)
  }, [notes, saved, dataset, model])

  // Handle external append (from QueryImagePanel)
  useEffect(() => {
    if (!appendToSummary) return
    setNotes(prev => {
      const existing = prev.summary.trim()
      return { ...prev, summary: existing ? `${existing}\n\n---\n\n${appendToSummary}` : appendToSummary }
    })
    setSaved(false)
    onAppendConsumed?.()
  }, [appendToSummary, onAppendConsumed])

  const update = useCallback((field: keyof Notes, value: string) => {
    setNotes(prev => ({ ...prev, [field]: value }))
    setSaved(false)
    setCopied(false)
  }, [])

  const clearNotes = () => {
    if (!confirm('Clear all diagnostics notes for this dataset/model pair?')) return
    setNotes(EMPTY)
    if (dataset && model) localStorage.removeItem(storageKey(dataset, model))
    setSaved(true)
  }

  const buildSummaryText = (): string => {
    const lines: string[] = [
      `Current diagnostics summary — ${new Date().toISOString().slice(0, 19).replace('T', ' ')} UTC`,
      `Dataset: ${dataset}`,
      `Model: ${model}`,
      '',
    ]

    if (embeddingAnalysis) {
      lines.push('Embedding analysis:')
      lines.push(`- embeddings: ${embeddingAnalysis.count}`)
      lines.push(`- dimension: ${embeddingAnalysis.dimension}`)
      lines.push(`- norm mean: ${embeddingAnalysis.norm_mean}`)
      lines.push(`- cluster separation: ${embeddingAnalysis.cluster_separation}`)
      lines.push(`- intra-class: ${embeddingAnalysis.intra_class_mean}`)
      lines.push(`- inter-class: ${embeddingAnalysis.inter_class_mean}`)
      lines.push(`- pairwise mean: ${embeddingAnalysis.pairwise_mean}`)
      lines.push(`- pairs sampled: ${embeddingAnalysis.pairs_sampled}`)
      lines.push('')
    } else {
      lines.push('Embedding analysis: not loaded yet', '')
    }

    if (neighborResult) {
      lines.push('Nearest neighbors:')
      lines.push(`- NN agreement: ${neighborResult.nn_agreement}/${neighborResult.total} (${(neighborResult.nn_agreement_rate * 100).toFixed(1)}%)`)
      lines.push('')
    } else {
      lines.push('Nearest neighbors: not loaded yet', '')
    }

    if (selectedPoint) {
      lines.push('Selected PCA point:')
      lines.push(`- label: ${selectedPoint.label}`)
      lines.push(`- region: ${selectedPoint.region_code}`)
      lines.push(`- split: ${selectedPoint.split}`)
      lines.push(`- id: ${shortId(selectedPoint.reference_image_id)}`)
      lines.push(`- x: ${selectedPoint.x.toFixed(3)}, y: ${selectedPoint.y.toFixed(3)}`)
      lines.push('')
    }

    lines.push('Reminder: diagnostics validate embedding behavior, not authentication accuracy.')
    return lines.join('\n')
  }

  const insertSummary = () => {
    const text = buildSummaryText()
    setNotes(prev => {
      const existing = prev.summary.trim()
      const newValue = existing ? `${existing}\n\n---\n\n${text}` : text
      return { ...prev, summary: newValue }
    })
    setSaved(false)
    setCopied(false)
  }

  const generateMarkdown = (): string => {
    const lines: string[] = [
      `## Diagnostics Observation — ${dataset} / ${model}`,
      '',
      `**Date:** ${new Date().toISOString().slice(0, 19).replace('T', ' ')} UTC`,
      '',
    ]

    if (embeddingAnalysis) {
      lines.push('### Embedding Summary', '')
      lines.push(`- Embeddings: ${embeddingAnalysis.count}`)
      lines.push(`- Dimension: ${embeddingAnalysis.dimension}`)
      lines.push(`- Norm mean: ${embeddingAnalysis.norm_mean}`)
      lines.push(`- Cluster separation: ${embeddingAnalysis.cluster_separation}`)
      lines.push(`- Intra-class: ${embeddingAnalysis.intra_class_mean}`)
      lines.push(`- Inter-class: ${embeddingAnalysis.inter_class_mean}`)
      lines.push('')
    }

    if (neighborResult) {
      lines.push('### Nearest-Neighbor Summary', '')
      lines.push(`- NN agreement: ${neighborResult.nn_agreement}/${neighborResult.total} (${(neighborResult.nn_agreement_rate * 100).toFixed(1)}%)`)
      lines.push('')
    }

    if (selectedPoint) {
      lines.push('### Selected PCA Point', '')
      lines.push(`- ID: ${selectedPoint.reference_image_id}`)
      lines.push(`- Label: ${selectedPoint.label}`)
      lines.push(`- Region: ${selectedPoint.region_code}`)
      lines.push(`- Split: ${selectedPoint.split}`)
      lines.push(`- x: ${selectedPoint.x.toFixed(4)}, y: ${selectedPoint.y.toFixed(4)}`)
      lines.push('')
    }

    const sections: [keyof Notes, string][] = [
      ['summary', 'Current Diagnostics Summary'],
      ['pca', 'PCA Observations'],
      ['neighbors', 'Nearest-Neighbor Observations'],
      ['clusters', 'Unexpected Clusters / Outliers'],
      ['dataIssue', 'Possible Data Issue'],
      ['modelIssue', 'Possible Model Issue'],
      ['followUp', 'Follow-Up Actions'],
    ]
    for (const [key, title] of sections) {
      if (notes[key].trim()) {
        lines.push(`### ${title}`, '', notes[key].trim(), '')
      }
    }

    lines.push('---', '')
    lines.push('*Diagnostics observations do not indicate authentication accuracy.*')

    return lines.join('\n')
  }

  const copyMarkdown = async () => {
    const md = generateMarkdown()
    await navigator.clipboard.writeText(md)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (!dataset || !model) return null

  const hasContent = Object.values(notes).some(v => v.trim())

  return (
    <div className="panel">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>Diagnostics Notes
          <span style={{ fontSize: 10, color: 'var(--text-dim)', fontWeight: 'normal', marginLeft: 8 }}>
            {saved ? 'saved locally' : 'unsaved…'}
          </span>
        </h3>
        <div className="flex-row">
          <button onClick={insertSummary} title="Insert current metrics into the summary field">
            Insert Summary
          </button>
          <button onClick={copyMarkdown} disabled={!hasContent} style={{ marginLeft: 4 }}>
            {copied ? '✓ Copied' : 'Copy Markdown'}
          </button>
          <button onClick={clearNotes} disabled={!hasContent} style={{ marginLeft: 4 }}>Clear</button>
        </div>
      </div>
      <p style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 4 }}>
        Notes are stored in browser localStorage per dataset/model pair. Use Copy Markdown to paste into the learning log.
      </p>

      {/* Summary field — full width */}
      <div className="field mt-8">
        <label>Current diagnostics summary <span style={{ fontSize: 10, color: 'var(--text-dim)' }}>(auto-fillable via Insert Summary)</span></label>
        <textarea
          value={notes.summary}
          onChange={e => update('summary', e.target.value)}
          rows={6}
          style={{ resize: 'vertical', fontSize: 11, fontFamily: 'monospace' }}
        />
      </div>

      <div className="grid-2 mt-8">
        {([
          ['pca', 'PCA observations'],
          ['neighbors', 'Nearest-neighbor observations'],
          ['clusters', 'Unexpected clusters / outliers'],
          ['dataIssue', 'Possible data issue'],
          ['modelIssue', 'Possible model issue'],
          ['followUp', 'Follow-up actions'],
        ] as [keyof Notes, string][]).map(([key, label]) => (
          <div key={key} className="field">
            <label>{label}</label>
            <textarea
              value={notes[key]}
              onChange={e => update(key, e.target.value)}
              rows={3}
              style={{ resize: 'vertical', fontSize: 12 }}
            />
          </div>
        ))}
      </div>
    </div>
  )
}
