import { useState } from 'react'
import { createSession } from '../api/captureApi'

interface Props {
  deviceId: string | null
  calibrationId: string | null
  protocolCode: string | null
  sessionId: string | null
  onSessionCreated: (id: string) => void
  onError: (msg: string) => void
}

export default function CaptureSessionPanel({ deviceId, calibrationId, protocolCode, sessionId, onSessionCreated, onError }: Props) {
  const [operator, setOperator] = useState('')
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(false)

  const doCreate = async () => {
    if (!deviceId || !protocolCode) return
    setLoading(true)
    try {
      const s = await createSession({
        device_id: deviceId,
        calibration_id: calibrationId || undefined,
        capture_protocol_code: protocolCode,
        source_type: 'local_workbench',
        operator: operator || undefined,
        notes: notes || undefined,
      })
      onSessionCreated(s.id)
      localStorage.setItem('workbench_session_id', s.id)
    } catch (e) { onError(String(e)) }
    setLoading(false)
  }

  const ready = deviceId && protocolCode

  return (
    <div className="panel">
      <h3>Capture Session {sessionId && <span className="badge pass" style={{ marginLeft: 8 }}>{sessionId.slice(0, 8)}...</span>}</h3>
      {sessionId ? (
        <div>
          <p className="mono">Session: {sessionId}</p>
          <button className="mt-8" onClick={() => navigator.clipboard.writeText(sessionId)}>Copy ID</button>
        </div>
      ) : (
        <>
          {!ready && <p className="mono">Select device and protocol first</p>}
          {ready && (
            <div className="grid-2">
              <div className="field"><label>Operator (optional)</label><input value={operator} onChange={e => setOperator(e.target.value)} /></div>
              <div className="field"><label>Notes (optional)</label><input value={notes} onChange={e => setNotes(e.target.value)} /></div>
              <div className="field"><button onClick={doCreate} disabled={loading}>Create Session</button></div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
