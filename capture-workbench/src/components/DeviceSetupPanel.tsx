import { useState } from 'react'
import { registerDevice, getDevice } from '../api/deviceApi'
import type { DeviceResponse } from '../api/types'

const ORG_ID = 'a0000000-0000-0000-0000-000000000001'

interface Props {
  device: DeviceResponse | null
  onDeviceSet: (d: DeviceResponse) => void
  onError: (msg: string) => void
}

export default function DeviceSetupPanel({ device, onDeviceSet, onError }: Props) {
  const [mode, setMode] = useState<'register' | 'existing'>('register')
  const [serial, setSerial] = useState('LOCAL-MICROSCOPE-001')
  const [deviceType, setDeviceType] = useState('HANDHELD_MICROSCOPE')
  const [firmware, setFirmware] = useState('')
  const [existingId, setExistingId] = useState('')
  const [loading, setLoading] = useState(false)

  const doRegister = async () => {
    setLoading(true)
    try {
      const d = await registerDevice({ device_serial: serial, device_type: deviceType, organization_id: ORG_ID, firmware_version: firmware || undefined })
      onDeviceSet(d)
      localStorage.setItem('workbench_device_id', d.id)
    } catch (e) { onError(String(e)) }
    setLoading(false)
  }

  const doLoad = async () => {
    setLoading(true)
    try {
      const d = await getDevice(existingId)
      onDeviceSet(d)
      localStorage.setItem('workbench_device_id', d.id)
    } catch (e) { onError(String(e)) }
    setLoading(false)
  }

  return (
    <div className="panel">
      <h3>Device Setup {device && <span className="badge pass" style={{ marginLeft: 8 }}>{device.device_serial}</span>}</h3>
      <div className="flex-row mb-8">
        <button onClick={() => setMode('register')} disabled={mode === 'register'}>Register New</button>
        <button onClick={() => setMode('existing')} disabled={mode === 'existing'}>Use Existing</button>
      </div>
      {mode === 'register' ? (
        <div className="grid-2">
          <div className="field"><label>Serial</label><input value={serial} onChange={e => setSerial(e.target.value)} /></div>
          <div className="field"><label>Type</label><input value={deviceType} onChange={e => setDeviceType(e.target.value)} /></div>
          <div className="field"><label>Firmware (optional)</label><input value={firmware} onChange={e => setFirmware(e.target.value)} /></div>
          <div className="field" style={{ display: 'flex', alignItems: 'flex-end' }}>
            <button onClick={doRegister} disabled={loading || !serial}>Register Device</button>
          </div>
        </div>
      ) : (
        <div className="grid-2">
          <div className="field"><label>Device ID</label><input value={existingId} onChange={e => setExistingId(e.target.value)} placeholder="paste UUID" /></div>
          <div className="field" style={{ display: 'flex', alignItems: 'flex-end' }}>
            <button onClick={doLoad} disabled={loading || !existingId}>Load Device</button>
          </div>
        </div>
      )}
    </div>
  )
}
