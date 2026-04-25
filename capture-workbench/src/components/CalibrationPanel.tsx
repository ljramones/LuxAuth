import { useState } from 'react'
import { createCalibration } from '../api/deviceApi'

interface Props {
  deviceId: string | null
  calibrationId: string | null
  onCalibrationSet: (id: string) => void
  onError: (msg: string) => void
}

export default function CalibrationPanel({ deviceId, calibrationId, onCalibrationSet, onError }: Props) {
  const [scaleRef, setScaleRef] = useState(true)
  const [wbRef, setWbRef] = useState(true)
  const [mag, setMag] = useState('')
  const [lighting, setLighting] = useState('')
  const [loading, setLoading] = useState(false)

  const doCreate = async () => {
    if (!deviceId) return
    setLoading(true)
    try {
      const cal = await createCalibration(deviceId, {
        calibration_profile: {
          name: `workbench_cal_${Date.now()}`,
          scale_reference_used: scaleRef,
          white_balance_reference_used: wbRef,
          magnification_profile: mag || undefined,
          lighting_profile: lighting || undefined,
        },
      })
      onCalibrationSet(cal.id)
      localStorage.setItem('workbench_calibration_id', cal.id)
    } catch (e) { onError(String(e)) }
    setLoading(false)
  }

  return (
    <div className="panel">
      <h3>Calibration {calibrationId && <span className="badge pass" style={{ marginLeft: 8 }}>Active</span>}
        {!calibrationId && deviceId && <span className="badge pending" style={{ marginLeft: 8 }}>Not set</span>}
      </h3>
      {!deviceId && <p className="mono">Select a device first</p>}
      {deviceId && (
        <div className="grid-2">
          <div className="field"><label><input type="checkbox" checked={scaleRef} onChange={e => setScaleRef(e.target.checked)} /> Scale reference used</label></div>
          <div className="field"><label><input type="checkbox" checked={wbRef} onChange={e => setWbRef(e.target.checked)} /> White balance reference used</label></div>
          <div className="field"><label>Magnification</label><input value={mag} onChange={e => setMag(e.target.value)} placeholder="e.g., 200x" /></div>
          <div className="field"><label>Lighting</label><input value={lighting} onChange={e => setLighting(e.target.value)} placeholder="e.g., POLARIZED_RING" /></div>
          <div className="field"><button onClick={doCreate} disabled={loading}>Create Calibration</button></div>
        </div>
      )}
    </div>
  )
}
