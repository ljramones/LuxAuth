import { useEffect, useState } from 'react'
import { checkHealth, endpoints } from '../api/client'

interface ServiceStatus { name: string; url: string; ok: boolean | null; service?: string }

export default function BackendStatusPanel() {
  const [services, setServices] = useState<ServiceStatus[]>([
    { name: 'Device Service', url: endpoints.device, ok: null },
    { name: 'Capture Intake', url: endpoints.capture, ok: null },
    { name: 'Image Quality', url: endpoints.quality, ok: null },
    { name: 'Normalization', url: endpoints.normalization, ok: null },
  ])

  const refresh = async () => {
    const updated = await Promise.all(
      services.map(async (s) => {
        const result = await checkHealth(s.url)
        return { ...s, ok: result.ok, service: result.service }
      })
    )
    setServices(updated)
  }

  useEffect(() => { refresh() }, [])

  return (
    <div className="panel">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>Backend Services</h3>
        <button onClick={refresh}>Refresh</button>
      </div>
      <div className="grid-2 mt-8">
        {services.map((s) => (
          <div key={s.name} className="flex-row mb-4">
            <span className={`status-dot ${s.ok === null ? 'yellow' : s.ok ? 'green' : 'red'}`} />
            <span style={{ fontSize: 13 }}>{s.name}</span>
            <span className="mono" style={{ marginLeft: 'auto' }}>
              {s.ok === null ? '...' : s.ok ? 'OK' : 'DOWN'}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
