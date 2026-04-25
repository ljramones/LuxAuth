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
import { getSessionStatus, completeSession } from './api/captureApi'
import { getQualityReport } from './api/qualityApi'
import { getNormalizationResult } from './api/normalizationApi'
import type { DeviceResponse, CaptureProtocol, RegionStatus, ImageUploadResponse, QualityReport, NormalizationResult, CompleteSessionResponse } from './api/types'

interface UploadedImage {
  response: ImageUploadResponse
  preview: string
  quality: QualityReport | null
  normalization: NormalizationResult | null
}

export default function App() {
  const [error, setError] = useState<string | null>(null)
  const [device, setDevice] = useState<DeviceResponse | null>(null)
  const [calibrationId, setCalibrationId] = useState<string | null>(null)
  const [protocol, setProtocol] = useState<CaptureProtocol | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [regions, setRegions] = useState<RegionStatus[]>([])
  const [uploads, setUploads] = useState<UploadedImage[]>([])
  const [completionResult, setCompletionResult] = useState<CompleteSessionResponse | null>(null)
  const [itemId, setItemId] = useState('local_capture_item_001')

  // Restore from localStorage
  useEffect(() => {
    const savedDevice = localStorage.getItem('workbench_device_id')
    if (savedDevice) {
      import('./api/deviceApi').then(m => m.getDevice(savedDevice).then(setDevice).catch(() => {}))
    }
    const savedCal = localStorage.getItem('workbench_calibration_id')
    if (savedCal) setCalibrationId(savedCal)
  }, [])

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

  return (
    <Layout>
      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

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
    </Layout>
  )
}
