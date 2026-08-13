import { defaultEditorValue, type RequestEditorValue, type RequestRow } from '../RequestEditor'
import type { RequestDraft, RequestItem, RequestSavePayload } from '../types/api'

export const fingerprint = (value: unknown): string => JSON.stringify(value)

const normalizeRows = (rows?: RequestRow[] | null): RequestRow[] =>
  (rows || []).map(row => ({
    id: row.id,
    client_id: row.client_id,
    enabled: row.enabled !== false,
    key: row.key || '',
    value: row.value || '',
    description: row.description || '',
  }))

export const editorFromRequest = (request?: RequestItem | null): RequestEditorValue =>
  request
    ? {
        description: request.description || null,
        headers: normalizeRows(request.headers),
        query_parameters: normalizeRows(request.query_parameters),
        authorization: request.authorization || { type: 'none' },
        body: request.body || null,
        body_type: request.body_type || 'none',
        timeout: request.timeout || 30,
        follow_redirects: request.follow_redirects !== false,
        verify_ssl: request.verify_ssl !== false,
      }
    : defaultEditorValue()

const rowsForPayload = (rows: RequestRow[]): Array<Omit<RequestRow, 'id'>> =>
  rows
    .filter(row => row.key.trim())
    .map(row => ({
      key: row.key.trim(),
      value: row.value || '',
      description: row.description?.trim() || null,
      enabled: row.enabled !== false,
    }))

export const editorPayload = (editor: RequestEditorValue) => ({
  description: editor.description || null,
  headers: rowsForPayload(editor.headers),
  query_parameters: rowsForPayload(editor.query_parameters),
  authorization: editor.authorization || { type: 'none' as const },
  body: editor.body_type === 'none' ? null : editor.body || '',
  body_type: editor.body_type,
  timeout: editor.timeout,
  follow_redirects: editor.follow_redirects,
  verify_ssl: editor.verify_ssl,
})

export const defaultDraft = (collectionId?: string | null): RequestDraft => ({
  name: 'Untitled request',
  method: 'GET',
  url: '',
  collection_id: collectionId || null,
  editor: defaultEditorValue(),
})

export const draftFromRequest = (request: RequestItem): RequestDraft => ({
  name: request.name,
  method: request.method,
  url: request.url,
  collection_id: request.collection_id || null,
  editor: editorFromRequest(request),
})

export const savePayloadFromDraft = (draft: RequestDraft, active: RequestItem | null): RequestSavePayload => ({
  name: draft.name.trim() || 'Untitled request',
  method: draft.method,
  url: draft.url,
  collection_id: draft.collection_id !== undefined ? draft.collection_id : (active?.collection_id || null),
  environment_id: active?.environment_id || null,
  is_favorite: active?.is_favorite || false,
  ...editorPayload(draft.editor),
})
