export type Role = 'admin' | 'operator' | 'readonly'
export type CameraStatus = 'active' | 'inactive'
export type EventDirection = 'entry' | 'exit'
export type EventStatus = 'automatic' | 'corrected' | 'removed'
export type LineDirection = 'entry' | 'exit' | 'both'

export interface User {
  id: string
  email: string
  full_name: string
  role: Role
  is_active: boolean
  created_at: string
}

export interface Camera {
  id: string
  name: string
  status: CameraStatus
  processing_fps: number
  processing_width: number
  processing_height: number
  min_confidence: number
  is_online: boolean
  last_seen_at?: string
  created_at: string
}

export interface CameraCreate {
  name: string
  rtsp_url: string
  username?: string
  password?: string
  status: CameraStatus
  processing_fps: number
  processing_width: number
  processing_height: number
  min_confidence: number
}

export interface CountingLine {
  id: string
  camera_id: string
  x1_relative: number
  y1_relative: number
  x2_relative: number
  y2_relative: number
  direction: LineDirection
  active_classes: string[]
  created_at: string
}

export interface VehicleEvent {
  id: string
  camera_id: string
  event_time: string
  vehicle_type: string
  confidence: number
  direction: EventDirection
  tracker_id?: number
  bbox_x1: number
  bbox_y1: number
  bbox_x2: number
  bbox_y2: number
  snapshot_path?: string
  status: EventStatus
  observation?: string
  created_at: string
}

export interface HourlyCount {
  hour: number
  count: number
}

export interface DailyCount {
  date: string
  count: number
}

export interface DashboardMetrics {
  today_count: number
  week_count: number
  month_count: number
  hourly_counts: HourlyCount[]
  daily_counts: DailyCount[]
  recent_events: VehicleEvent[]
  camera_online: boolean
  worker_running: boolean
}

export interface SystemLog {
  id: string
  level: string
  source: string
  message: string
  details?: Record<string, unknown>
  created_at: string
}

export interface AppSetting {
  id: string
  key: string
  value: unknown
  description?: string
  updated_at: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface EventFilter {
  camera_id?: string
  vehicle_type?: string
  direction?: EventDirection
  status?: EventStatus
  date_from?: string
  date_to?: string
  page?: number
  page_size?: number
}
