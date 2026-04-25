export interface HealthStatus {
  status: string
  service: string
}

export interface DeviceRegisterRequest {
  device_serial: string
  device_type: string
  organization_id: string
  firmware_version?: string
}

export interface DeviceResponse {
  id: string
  device_serial: string
  device_type: string
  status: string
  firmware_version?: string
  created_at: string
}

export interface CalibrationRequest {
  calibration_profile: {
    name: string
    scale_reference_used: boolean
    white_balance_reference_used: boolean
    magnification_profile?: string
    lighting_profile?: string
    notes?: string
  }
}

export interface CalibrationResponse {
  id: string
  device_id: string
  calibrated_at: string
  status: string
}

export interface ProtocolRegion {
  region_code: string
  display_name: string
  min_images: number
  magnification_profile?: string
  lighting_profile?: string
}

export interface CaptureProtocol {
  id: string
  protocol_code: string
  protocol_version: string
  brand?: string
  category?: string
  material?: string
  description?: string
  regions: ProtocolRegion[]
}

export interface CreateCaptureSessionRequest {
  device_id: string
  calibration_id?: string
  capture_protocol_code: string
  source_type: string
  operator?: string
  notes?: string
}

export interface CaptureSessionResponse {
  id: string
  status: string
  capture_protocol_code: string
}

export interface RegionStatus {
  region_code: string
  required: number
  uploaded: number
  satisfied: boolean
}

export interface SessionStatusResponse {
  capture_session_id: string
  status: string
  protocol_code: string
  all_regions_satisfied: boolean
  total_images: number
  missing_regions: string[]
  region_status: RegionStatus[]
}

export interface ImageUploadResponse {
  id: string
  image_asset_id: string
  capture_session_id: string
  region_code: string
  raw_object_uri: string
  width?: number
  height?: number
  sha256_checksum?: string
}

export interface QualityReport {
  image_asset_id: string
  sharpness_score: number
  exposure_score: number
  glare_score: number
  quality_status: string
  issues: string[]
}

export interface NormalizationResult {
  image_asset_id: string
  normalized_object_uri: string
  preprocessing_version: string
}

export interface CompleteSessionResponse {
  capture_session_id: string
  status: string
  all_regions_satisfied: boolean
  total_images: number
  missing_regions: string[]
  region_status: RegionStatus[]
}
