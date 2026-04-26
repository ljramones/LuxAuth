import { useState, useCallback, useEffect } from 'react'
import Layout from './components/Layout'
import BackendStatusPanel from './components/BackendStatusPanel'
import DeviceSetupPanel from './components/DeviceSetupPanel'
import CalibrationPanel from './components/CalibrationPanel'
import CaptureProtocolSelector from './components/CaptureProtocolSelector'
import CaptureSessionPanel from './components/CaptureSessionPanel'
import RegionChecklist from './components/RegionChecklist'
import ImageUploadCard from './components/ImageUploadCard'
import QualityResultCard from './components/QualityResultCard'
import NormalizedPreview from './components/NormalizedPreview'
import SessionSummary from './components/SessionSummary'
import ErrorBanner from './components/ErrorBanner'
import DatasetsPanel from './components/DatasetsPanel'
import EvaluationsPanel from './components/EvaluationsPanel'
import EmbeddingAnalysisPanel from './components/EmbeddingAnalysisPanel'
import ProjectionPanel from './components/ProjectionPanel'
import NeighborsPanel from './components/NeighborsPanel'
import DiagnosticsNotesPanel from './components/DiagnosticsNotesPanel'
import QueryImagePanel from './components/QueryImagePanel'
import DataExplorerTab from './components/DataExplorerTab'
import { getSessionStatus, completeSession } from './api/captureApi'
import { getQualityReport } from './api/qualityApi'
import { getNormalizationResult } from './api/normalizationApi'
import { getDatasetModels, type DatasetModelCompat, type DatasetSummary, type EmbeddingAnalysis, type NeighborResult, type ProjectionPoint } from './api/mlDiagnosticsApi'
import type { DeviceResponse, CaptureProtocol, RegionStatus, ImageUploadResponse, QualityReport, NormalizationResult, CompleteSessionResponse } from './api/types'

interface UploadedImage {
  response: ImageUploadResponse
  preview: string
  quality: QualityReport | null
  normalization: NormalizationResult | null
}

type Tab = 'capture' | 'diagnostics' | 'data-explorer'

export default function App() {
  const [tab, setTab] = useState<Tab>('capture')
  const [error, setError] = useState<string | null>(null)
  const [device, setDevice] = useState<DeviceResponse | null>(null)
  const [calibrationId, setCalibrationId] = useState<string | null>(null)
  const [protocol, setProtocol] = useState<CaptureProtocol | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [regions, setRegions] = useState<RegionStatus[]>([])
  const [uploads, setUploads] = useState<UploadedImage[]>([])
  const [completionResult, setCompletionResult] = useState<CompleteSessionResponse | null>(null)
  const [itemId, setItemId] = useState('local_capture_item_001')

  // Diagnostics state
  const [selectedDataset, setSelectedDataset] = useState<string | null>(null)
  const [datasetModels, setDatasetModels] = useState<DatasetModelCompat[]>([])
  const [selectedModel, setSelectedModel] = useState<string | null>(null)
  const [lastAnalysis, setLastAnalysis] = useState<EmbeddingAnalysis | null>(null)
  const [lastNeighbors, setLastNeighbors] = useState<NeighborResult | null>(null)
  const [lastSelectedPoint, setLastSelectedPoint] = useState<ProjectionPoint | null>(null)
  const [queryNoteText, setQueryNoteText] = useState<string | null>(null)

  // Restore from localStorage
  useEffect(() => {
    const savedDevice = localStorage.getItem('workbench_device_id')
    if (savedDevice) {
      import('./api/deviceApi').then(m => m.getDevice(savedDevice).then(setDevice).catch(() => {}))
    }
    const savedCal = localStorage.getItem('workbench_calibration_id')
    if (savedCal) setCalibrationId(savedCal)
  }, [])

  // Load models when dataset is selected
  useEffect(() => {
    if (selectedDataset) {
      getDatasetModels(selectedDataset).then(m => {
        setDatasetModels(m)
        // Auto-select first compatible model
        const compatible = m.find(x => x.compatible)
        if (compatible && !selectedModel) {
          setSelectedModel(compatible.model_version)
        }
      }).catch(() => setDatasetModels([]))
    } else {
      setDatasetModels([])
    }
  }, [selectedDataset])

  const refreshStatus = useCallback(async () => {
    if (!sessionId) return
    try {
      const s = await getSessionStatus(sessionId)
      setRegions(s.region_status)
    } catch (e) { setError(String(e)) }
  }, [sessionId])

  useEffect(() => { if (sessionId) refreshStatus() }, [sessionId, refreshStatus])

  const handleUpload = async (resp: ImageUploadResponse) => {
    const entry: UploadedImage = { response: resp, preview: '', quality: null, normalization: null }
    setUploads(prev => [...prev, entry])
    refreshStatus()

    // Poll for quality and normalization
    const poll = async () => {
      for (let i = 0; i < 15; i++) {
        await new Promise(r => setTimeout(r, 2000))
        const q = await getQualityReport(resp.image_asset_id)
        if (q) {
          setUploads(prev => prev.map(u => u.response.id === resp.id ? { ...u, quality: q } : u))
          const n = await getNormalizationResult(resp.image_asset_id)
          if (n) {
            setUploads(prev => prev.map(u => u.response.id === resp.id ? { ...u, normalization: n } : u))
          }
          return
        }
      }
    }
    poll()
  }

  const handleComplete = async () => {
    if (!sessionId) return
    try {
      const r = await completeSession(sessionId)
      setCompletionResult(r)
      refreshStatus()
    } catch (e) { setError(String(e)) }
  }

  const resetState = () => {
    setSessionId(null)
    setRegions([])
    setUploads([])
    setCompletionResult(null)
    localStorage.removeItem('workbench_session_id')
  }

  const handleDatasetSelect = (ds: DatasetSummary) => {
    setSelectedDataset(ds.dataset_version)
  }

  return (
    <Layout>
      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <button
          onClick={() => setTab('capture')}
          style={{ fontWeight: tab === 'capture' ? 'bold' : 'normal', opacity: tab === 'capture' ? 1 : 0.6 }}
        >
          Capture
        </button>
        <button
          onClick={() => setTab('diagnostics')}
          style={{ fontWeight: tab === 'diagnostics' ? 'bold' : 'normal', opacity: tab === 'diagnostics' ? 1 : 0.6 }}
        >
          ML Diagnostics
        </button>
        <button
          onClick={() => setTab('data-explorer')}
          style={{ fontWeight: tab === 'data-explorer' ? 'bold' : 'normal', opacity: tab === 'data-explorer' ? 1 : 0.6 }}
        >
          Data Explorer
        </button>
      </div>

      {tab === 'capture' && (
        <>
          <BackendStatusPanel />
          <DeviceSetupPanel device={device} onDeviceSet={setDevice} onError={setError} />
          <CalibrationPanel deviceId={device?.id || null} calibrationId={calibrationId} onCalibrationSet={setCalibrationId} onError={setError} />
          <CaptureProtocolSelector protocol={protocol} onProtocolSet={setProtocol} onError={setError} />
          <CaptureSessionPanel
            deviceId={device?.id || null}
            calibrationId={calibrationId}
            protocolCode={protocol?.protocol_code || null}
            sessionId={sessionId}
            onSessionCreated={setSessionId}
            onError={setError}
          />

          {sessionId && (
            <>
              <RegionChecklist regions={regions} onRefresh={refreshStatus} />

              <div className="panel">
                <h3>Upload Images</h3>
                <div className="field mb-8">
                  <label>External Item ID</label>
                  <input value={itemId} onChange={e => setItemId(e.target.value)} style={{ maxWidth: 300 }} />
                </div>
                {protocol?.regions.map(r => (
                  <div key={r.region_code} className="mb-8">
                    <p className="mono mb-4">{r.region_code} (min {r.min_images})</p>
                    <div className="flex-row flex-wrap">
                      {uploads.filter(u => u.response.region_code === r.region_code).map(u => (
                        <div key={u.response.id} style={{ margin: 4 }}>
                          <div style={{ fontSize: 11, color: 'var(--text-dim)' }}>
                            {u.response.image_asset_id.slice(0, 8)}...
                          </div>
                          {u.quality && <QualityResultCard report={u.quality} />}
                          {u.normalization && <NormalizedPreview result={u.normalization} />}
                          {!u.quality && <span className="badge pending">Processing...</span>}
                        </div>
                      ))}
                      <ImageUploadCard
                        sessionId={sessionId}
                        deviceId={device?.id || ''}
                        regionCode={r.region_code}
                        externalItemId={itemId}
                        onUploaded={handleUpload}
                        onError={setError}
                      />
                    </div>
                  </div>
                ))}
              </div>

              <div className="panel">
                <div className="flex-row">
                  <button onClick={handleComplete}>Complete Session</button>
                  <button onClick={resetState} style={{ marginLeft: 8 }}>New Session</button>
                </div>
              </div>

              {completionResult && <SessionSummary result={completionResult} />}
            </>
          )}
        </>
      )}

      {tab === 'diagnostics' && (() => {
        const currentModelCompat = datasetModels.find(m => m.model_version === selectedModel)
        const embeddingCount = currentModelCompat?.embedding_count ?? 0
        const isCompatible = currentModelCompat?.compatible ?? false

        return (
          <>
            <DatasetsPanel onSelect={handleDatasetSelect} selected={selectedDataset} />

            <div className="panel">
              <h3>Model {!selectedDataset && <span style={{ fontSize: 11, color: 'var(--yellow)', fontWeight: 'normal' }}> — select a dataset first</span>}</h3>
              {selectedDataset ? (
                <>
                  <select
                    value={selectedModel || ''}
                    onChange={e => setSelectedModel(e.target.value || null)}
                    style={{ minWidth: 400 }}
                  >
                    <option value="">Select a model...</option>
                    {datasetModels.map(m => (
                      <option key={m.model_version} value={m.model_version}>
                        {m.model_version} — {m.compatible ? `${m.embedding_count} embeddings` : 'no embeddings'}
                      </option>
                    ))}
                  </select>
                  {datasetModels.length === 0 && (
                    <p className="mono mt-8" style={{ color: 'var(--text-dim)' }}>No models found for this dataset.</p>
                  )}
                </>
              ) : (
                <p className="mono" style={{ fontSize: 12 }}>Select a dataset row above to see available models.</p>
              )}
            </div>

            {/* Selection + compatibility summary */}
            <div className="panel" style={{ background: 'var(--bg)', border: '1px solid var(--border)', padding: '10px 16px' }}>
              <div style={{ fontSize: 12 }}>
                <div className="flex-row mb-4">
                  <span>Dataset:</span>
                  {selectedDataset
                    ? <span className="badge pass" style={{ marginLeft: 8 }}>{selectedDataset}</span>
                    : <span className="badge fail" style={{ marginLeft: 8 }}>Not selected</span>
                  }
                  <span style={{ marginLeft: 16 }}>Model:</span>
                  {selectedModel
                    ? <span className={`badge ${isCompatible ? 'pass' : 'fail'}`} style={{ marginLeft: 8 }}>{selectedModel}</span>
                    : <span className="badge fail" style={{ marginLeft: 8 }}>Not selected</span>
                  }
                </div>
                {selectedModel && selectedDataset && isCompatible && (
                  <p style={{ color: 'var(--green)' }}>
                    ✓ {embeddingCount} embeddings available — Analyze / Load / Inspect are ready
                  </p>
                )}
                {selectedModel && selectedDataset && !isCompatible && (
                  <div>
                    <p style={{ color: 'var(--red)' }}>✕ No embeddings for this dataset/model pair</p>
                    <p className="mono mt-8" style={{ color: 'var(--text-dim)', fontSize: 11, background: 'var(--surface)', padding: 8, borderRadius: 4 }}>
                      cd auth-platform<br />
                      make reembed-reference-data DATASET={selectedDataset} MODEL={selectedModel}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Section nav */}
            <div className="flex-row" style={{ gap: 4, marginBottom: 12, flexWrap: 'wrap' }}>
              {[
                ['query-image', 'Query Image'],
                ['evaluations', 'Evaluations'],
                ['embedding-analysis', 'Embeddings'],
                ['pca-projection', 'PCA'],
                ['nearest-neighbors', 'Neighbors'],
                ['diagnostics-notes', 'Notes'],
              ].map(([id, label]) => (
                <button key={id} onClick={() => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
                  style={{ fontSize: 11, padding: '3px 10px' }}>{label}</button>
              ))}
            </div>

            {selectedDataset && selectedModel && isCompatible && (
              <p style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 12 }}>
                Use <strong>Query Image</strong> to upload a single diagnostic image and see nearest neighbors for the selected dataset/model.
              </p>
            )}

            <div id="query-image">
              <QueryImagePanel
                dataset={selectedDataset}
                model={isCompatible ? selectedModel : null}
                isCompatible={isCompatible}
                onNoteSummary={(text) => setQueryNoteText(text)}
              />
            </div>
            <div id="evaluations"><EvaluationsPanel /></div>
            <div id="embedding-analysis"><EmbeddingAnalysisPanel dataset={selectedDataset} model={isCompatible ? selectedModel : null} expectedEmbeddingCount={embeddingCount} onResult={setLastAnalysis} /></div>
            <div id="pca-projection"><ProjectionPanel dataset={selectedDataset} model={isCompatible ? selectedModel : null} onPointSelected={setLastSelectedPoint} /></div>
            <div id="nearest-neighbors"><NeighborsPanel dataset={selectedDataset} model={isCompatible ? selectedModel : null} onResult={setLastNeighbors} /></div>
            <div id="diagnostics-notes">
              <DiagnosticsNotesPanel
                dataset={selectedDataset}
                model={isCompatible ? selectedModel : null}
                embeddingAnalysis={lastAnalysis}
                neighborResult={lastNeighbors}
                selectedPoint={lastSelectedPoint}
                appendToSummary={queryNoteText}
                onAppendConsumed={() => setQueryNoteText(null)}
              />
            </div>
          </>
        )
      })()}

      {tab === 'data-explorer' && (
        <DataExplorerTab onOpenInDiagnostics={(dv) => { setSelectedDataset(dv); setTab('diagnostics') }} />
      )}
    </Layout>
  )
}
