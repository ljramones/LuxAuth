import { useEffect, useState } from 'react'
import { listProtocols, getProtocol } from '../api/captureApi'
import type { CaptureProtocol } from '../api/types'

interface Props {
  protocol: CaptureProtocol | null
  onProtocolSet: (p: CaptureProtocol) => void
  onError: (msg: string) => void
}

export default function CaptureProtocolSelector({ protocol, onProtocolSet, onError }: Props) {
  const [protocols, setProtocols] = useState<Array<{ protocol_code: string }>>([])

  useEffect(() => {
    listProtocols().then(p => setProtocols(p)).catch(e => onError(String(e)))
  }, [])

  const handleSelect = async (code: string) => {
    try {
      const p = await getProtocol(code)
      onProtocolSet(p)
    } catch (e) { onError(String(e)) }
  }

  return (
    <div className="panel">
      <h3>Capture Protocol {protocol && <span className="badge pass" style={{ marginLeft: 8 }}>{protocol.protocol_code}</span>}</h3>
      <div className="field">
        <label>Select Protocol</label>
        <select value={protocol?.protocol_code || ''} onChange={e => handleSelect(e.target.value)}>
          <option value="">-- choose --</option>
          {protocols.map(p => <option key={p.protocol_code} value={p.protocol_code}>{p.protocol_code}</option>)}
        </select>
      </div>
      {protocol && (
        <div className="mt-8">
          <p className="mono mb-4">Required regions:</p>
          {protocol.regions.map(r => (
            <div key={r.region_code} className="flex-row mb-4">
              <span style={{ fontSize: 13 }}>{r.region_code}</span>
              <span className="mono" style={{ marginLeft: 'auto' }}>min {r.min_images} images</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
