import type { BodyType, RequestAuthorization, RequestEditorValue, RequestRow } from '../RequestEditor'

export type CollectionSummary = {
  id: string
  name: string
}

export type EnvironmentSummary = {
  id: string
  name: string
  description?: string | null
  is_active: boolean
  created_at?: string
  updated_at?: string
}

export type EnvironmentVariable = {
  value: string
  enabled: boolean
  secret: boolean
  description?: string
}

export type EnvironmentDetail = EnvironmentSummary & {
  variables: Record<string, EnvironmentVariable>
}

export type RequestItem = {
  id: string
  name: string
  description?: string | null
  method: string
  url: string
  collection_id?: string | null
  environment_id?: string | null
  body?: string | null
  body_type?: BodyType
  timeout?: number
  follow_redirects?: boolean
  verify_ssl?: boolean
  is_favorite?: boolean
  headers?: RequestRow[] | null
  query_parameters?: RequestRow[] | null
  authorization?: RequestAuthorization | null
}

export type ConsoleLog = {
  timestamp: string
  level: 'INFO' | 'REQUEST' | 'SUCCESS' | 'WARNING' | 'ERROR'
  message: string
  details?: string | null
}

export type ExecutionResult = {
  status_code: number | null
  reason_phrase?: string | null
  status_text?: string | null
  headers: Record<string, string>
  body: string | null
  response_size?: number | null
  duration_ms: number
  content_type?: string | null
  cookies?: Record<string, string>
  redirect_count?: number
  error?: string | null
  console_logs?: ConsoleLog[]
}

export type RequestDraft = {
  name: string
  method: string
  url: string
  collection_id?: string | null
  editor: RequestEditorValue
}

export type RequestSavePayload = {
  name: string
  method: string
  url: string
  collection_id: string | null
  environment_id: string | null
  is_favorite: boolean
  description: string | null
  headers: Array<Omit<RequestRow, 'id'>>
  query_parameters: Array<Omit<RequestRow, 'id'>>
  authorization: RequestAuthorization
  body: string | null
  body_type: BodyType
  timeout: number
  follow_redirects: boolean
  verify_ssl: boolean
}
