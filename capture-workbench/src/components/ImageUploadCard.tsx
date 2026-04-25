import { useState, useRef } from 'react'
import { uploadImage } from '../api/captureApi'
import type { ImageUploadResponse } from '../api/types'

interface Props {
  sessionId: string
  deviceId: string
  regionCode: string
  externalItemId: string
  onUploaded: (resp: ImageUploadResponse) => void
  onError: (msg: string) => void
}

export default function ImageUploadCard({ sessionId, deviceId, regionCode, externalItemId, onUploaded, onError }: Props) {
  const [preview, setPreview] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = async (file: File) => {
    setPreview(URL.createObjectURL(file))
    setLoading(true)
    try {
      const resp = await uploadImage(sessionId, file, {
        region_code: regionCode,
        device_id: deviceId,
        external_item_id: externalItemId,
        capture_index: '0',
      })
      onUploaded(resp)
    } catch (e) { onError(String(e)) }
    setLoading(false)
  }

  return (
    <div style={{ display: 'inline-block', verticalAlign: 'top', margin: 4 }}>
      <div
        className="upload-zone"
        style={{ width: 140, height: 140, display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}
        onClick={() => inputRef.current?.click()}
      >
        {preview ? (
          <img src={preview} className="preview-thumb" alt="preview" style={{ maxWidth: '100%', maxHeight: '100%' }} />
        ) : (
          <span className="mono" style={{ fontSize: 11 }}>{loading ? 'Uploading...' : `+ ${regionCode}`}</span>
        )}
        <input ref={inputRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])} />
      </div>
    </div>
  )
}
