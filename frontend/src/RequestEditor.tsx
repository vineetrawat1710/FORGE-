import { useMemo, useRef, useState, type KeyboardEvent } from 'react'
import { Copy, Plus, Trash2 } from 'lucide-react'

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' | 'HEAD' | 'OPTIONS'
export type BodyType = 'none' | 'json' | 'text' | 'form' | 'multipart' | 'xml'
export type AuthorizationType = 'none' | 'bearer' | 'basic' | 'api_key'

export type RequestRow = { id?: string; client_id?: string; enabled: boolean; key: string; value: string; description?: string | null }
export type RequestAuthorization = {
  type: AuthorizationType
  token?: string | null
  username?: string | null
  password?: string | null
  api_key_name?: string | null
  api_key_value?: string | null
  api_key_in?: 'header' | 'query' | null
}
export type RequestEditorValue = {
  description?: string | null
  headers: RequestRow[]
  query_parameters: RequestRow[]
  authorization: RequestAuthorization
  body: string | null
  body_type: BodyType
  timeout: number
  follow_redirects: boolean
  verify_ssl: boolean
}

type TableKind = 'parameter' | 'header' | 'form'
type EditorRow = RequestRow & { client_id: string; secret?: boolean }

export const defaultEditorValue = (): RequestEditorValue => ({
  description: null,
  headers: [],
  query_parameters: [],
  authorization: { type: 'none' },
  body: null,
  body_type: 'none',
  timeout: 30,
  follow_redirects: true,
  verify_ssl: true,
})

const emptyRow = (): EditorRow => ({ client_id: crypto.randomUUID(), enabled: true, key: '', value: '', description: '' })
const rowKey = (row: EditorRow) => row.id || row.client_id
const toEditorRows = (rows: RequestRow[]) => [...rows.map(row => ({ ...row, client_id: row.client_id || row.id || crypto.randomUUID(), description: row.description || '', secret: row.key.toLowerCase() === 'authorization' })), emptyRow()]
const toRequestRows = (rows: EditorRow[]): RequestRow[] => rows.filter(row => row.key.trim() || row.value.trim() || (row.description || '').trim()).map(row => ({ id: row.id, client_id: row.client_id, enabled: row.enabled, key: row.key, value: row.value, description: row.description || null }))
const patchValue = (value: RequestEditorValue, patch: Partial<RequestEditorValue>) => ({ ...value, ...patch })

const rowsFromUrlEncodedBody = (body: string): RequestRow[] => {
  const params = new URLSearchParams(body)
  return Array.from(params.entries()).map(([key, value]) => ({ enabled: true, key, value, description: '' }))
}

const rowsFromMultipartBody = (body: string): RequestRow[] => {
  try {
    const parsed = JSON.parse(body)
    return Array.isArray(parsed) ? parsed.map(row => ({ enabled: row.enabled !== false, key: row.key || '', value: row.value || '', description: row.description || '' })) : []
  } catch {
    return []
  }
}

const rowsToUrlEncodedBody = (rows: RequestRow[]) => {
  const params = new URLSearchParams()
  rows.filter(row => row.enabled !== false && row.key.trim()).forEach(row => params.append(row.key.trim(), row.value || ''))
  return params.toString()
}

const rowsToMultipartBody = (rows: RequestRow[]) => JSON.stringify(rows.filter(row => row.key.trim()).map(row => ({ enabled: row.enabled !== false, key: row.key.trim(), value: row.value || '', description: row.description || null })))

function VariableText({ value }: { value: string }) {
  const parts = value.split(/(\{\{[^}]+\}\})/g)
  return <>{parts.map((part, index) => part.startsWith('{{') ? <span className="editor-variable" key={index}>{part}</span> : part)}</>
}

function EditorTable({ kind, rows: contractRows, onChange }: { kind: TableKind; rows: RequestRow[]; onChange: (rows: RequestRow[]) => void }) {
  const rows = useMemo(() => toEditorRows(contractRows), [contractRows])
  const [editing, setEditing] = useState<string | null>(null)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const inputRefs = useRef<Record<string, HTMLInputElement | null>>({})
  const label = kind === 'parameter' ? 'Parameter' : kind === 'header' ? 'Header' : 'Form Field'
  const commitRows = (next: EditorRow[]) => onChange(toRequestRows(next))
  const update = (id: string, field: keyof EditorRow, value: string | boolean) => {
    const next = rows.map(row => rowKey(row) === id ? { ...row, [field]: value } : row)
    commitRows(next)
    if (field === 'key') setErrors(current => ({ ...current, [id]: '' }))
  }
  const validate = (row: EditorRow) => {
    if (!row.key && !row.value) return ''
    if (!row.key) return kind === 'header' ? 'Header name is required' : 'Parameter name is required'
    const duplicate = rows.some(item => rowKey(item) !== rowKey(row) && item.enabled && item.key.trim().toLowerCase() === row.key.trim().toLowerCase() && item.key)
    return duplicate ? `Duplicate ${label.toLowerCase()} name` : ''
  }
  const finish = (row: EditorRow) => setErrors(current => ({ ...current, [rowKey(row)]: validate(row) }))
  const duplicate = (row: EditorRow) => {
    const index = rows.findIndex(item => rowKey(item) === rowKey(row))
    const copy = { ...row, id: undefined, client_id: crypto.randomUUID() }
    commitRows([...rows.slice(0, index + 1), copy, ...rows.slice(index + 1)])
  }
  const remove = (id: string) => commitRows(rows.filter(row => rowKey(row) !== id))
  const handleKey = (event: KeyboardEvent<HTMLInputElement>, row: EditorRow, field: keyof EditorRow) => {
    if (event.key === 'Escape') { setEditing(null); return }
    if (event.key === 'Enter') { event.preventDefault(); finish(row); const index = rows.findIndex(item => rowKey(item) === rowKey(row)); const next = rows[index + 1] || rows[index - 1]; if (next) inputRefs.current[`${rowKey(next)}-${field}`]?.focus() }
    if (event.key === 'Delete' && !row.key && !row.value) remove(rowKey(row))
  }
  return <div className="editor-table-wrap">
    <div className="editor-table" role="table" aria-label={`${label}s`}>
      <div className="editor-table-head" role="row"><span>Enabled</span><span>{label}</span><span>Value</span><span>Description <small>optional</small></span><span>Actions</span></div>
      {rows.map(row => <div className={`editor-table-row ${errors[rowKey(row)] ? 'has-error' : ''}`} role="row" key={rowKey(row)}>
        <label className="editor-check"><input type="checkbox" checked={row.enabled} onChange={event => update(rowKey(row), 'enabled', event.target.checked)} aria-label={`Enable ${label.toLowerCase()}`} /></label>
        {(['key', 'value', 'description'] as const).map(field => <div className={`editor-cell ${editing === `${rowKey(row)}-${field}` ? 'is-editing' : ''}`} key={field}>
          {editing === `${rowKey(row)}-${field}` || row[field] ? <input autoFocus={editing === `${rowKey(row)}-${field}`} ref={element => { inputRefs.current[`${rowKey(row)}-${field}`] = element }} value={row[field] || ''} placeholder={`Add ${field}`} aria-label={`${label} ${field}`} onFocus={() => setEditing(`${rowKey(row)}-${field}`)} onChange={event => update(rowKey(row), field, event.target.value)} onBlur={() => finish(row)} onKeyDown={event => handleKey(event, row, field)} /> : <button className="editor-cell-placeholder" onClick={() => setEditing(`${rowKey(row)}-${field}`)}>Add {field}</button>}
          {field === 'value' && row.secret && row.value && editing !== `${rowKey(row)}-${field}` ? <span className="editor-secret" aria-hidden="true">••••••••</span> : null}
          {field === 'key' && errors[rowKey(row)] ? <small className="editor-field-error">{errors[rowKey(row)]}</small> : null}
          {field === 'value' && row[field]?.endsWith('{{') ? <div className="editor-variable-suggestions" role="listbox">{['BASE_URL', 'TOKEN', 'USER_ID'].map(variable => <button type="button" key={variable} onMouseDown={event => event.preventDefault()} onClick={() => update(rowKey(row), 'value', `${row.value}${variable}}}`)}>{`{{${variable}}}`}</button>)}</div> : null}
        </div>)}
        <div className="editor-row-actions"><button type="button" title={`Duplicate ${label.toLowerCase()}`} aria-label={`Duplicate ${label.toLowerCase()}`} onClick={() => duplicate(row)}><Copy size={13} /></button><button type="button" title={`Delete ${label.toLowerCase()}`} aria-label={`Delete ${label.toLowerCase()}`} onClick={() => remove(rowKey(row))}><Trash2 size={13} /></button></div>
      </div>)}
    </div>
    <button type="button" className="editor-add-button" onClick={() => commitRows([...rows, emptyRow()])}><Plus size={13} /> Add {label}</button>
  </div>
}

function AuthorizationEditor({ value, onChange }: { value: RequestAuthorization; onChange: (value: RequestAuthorization) => void }) {
  const type = value.type || 'none'
  return <div className="editor-panel authorization-editor"><label className="editor-select-label">Authorization type<select value={type} onChange={event => onChange({ type: event.target.value as AuthorizationType })}><option value="none">No Auth</option><option value="bearer">Bearer Token</option><option value="api_key">API Key</option><option value="basic">Basic Auth</option><option value="none">OAuth 2</option></select></label>{type === 'bearer' && <label className="editor-field">Token<input value={value.token || ''} onChange={event => onChange({ ...value, token: event.target.value })} placeholder="{{TOKEN}}" /></label>}{type === 'api_key' && <div className="editor-field-grid"><label className="editor-field">Key<input value={value.api_key_name || ''} onChange={event => onChange({ ...value, api_key_name: event.target.value })} placeholder="X-API-Key" /></label><label className="editor-field">Value<input value={value.api_key_value || ''} onChange={event => onChange({ ...value, api_key_value: event.target.value })} placeholder="{{API_KEY}}" /></label><label className="editor-field">Location<select value={value.api_key_in || 'header'} onChange={event => onChange({ ...value, api_key_in: event.target.value as 'header' | 'query' })}><option value="header">Header</option><option value="query">Query params</option></select></label></div>}{type === 'basic' && <div className="editor-field-grid"><label className="editor-field">Username<input value={value.username || ''} onChange={event => onChange({ ...value, username: event.target.value })} /></label><label className="editor-field">Password<input type="password" value={value.password || ''} onChange={event => onChange({ ...value, password: event.target.value })} /></label></div>}</div>
}

function BodyEditor({ value, onChange, disabled }: { value: RequestEditorValue; onChange: (value: RequestEditorValue) => void; disabled?: boolean }) {
  const mode = value.body_type
  const body = value.body || ''
  const formRows = mode === 'form' ? rowsFromUrlEncodedBody(body) : mode === 'multipart' ? rowsFromMultipartBody(body) : []
  const lines = body.split('\n')
  const jsonError = useMemo(() => { if (mode !== 'json' || !body.trim()) return ''; try { JSON.parse(body); return '' } catch { return 'Invalid JSON' } }, [body, mode])
  const setMode = (body_type: BodyType) => onChange(patchValue(value, { body_type, body: body_type === 'none' ? null : body }))
  return <div className="editor-panel body-editor">{disabled ? <div className="editor-note">GET requests do not support a request body. Use another method to send body content.</div> : <div className="editor-mode-tabs" role="tablist">{[['json', 'Raw JSON'], ['multipart', 'Form Data'], ['form', 'x-www-form-urlencoded'], ['text', 'Binary'], ['xml', 'GraphQL']].map(([key, label]) => <button key={key} className={mode === key ? 'active' : ''} onClick={() => setMode(key as BodyType)}>{label}</button>)}</div>}{mode === 'json' || mode === 'xml' || mode === 'text' ? <div className={`code-editor${disabled ? ' is-disabled' : ''}`}><div className="code-lines" aria-hidden="true">{lines.map((_, index) => <span key={index}>{index + 1}</span>)}</div><textarea aria-label="Request body" value={body} onChange={event => onChange(patchValue(value, { body: event.target.value }))} spellCheck={false} readOnly={disabled} /></div> : !disabled ? <EditorTable kind="form" rows={formRows} onChange={rows => onChange(patchValue(value, { body: mode === 'form' ? rowsToUrlEncodedBody(rows) : rowsToMultipartBody(rows) }))} /> : null}{jsonError && !disabled ? <small className="editor-field-error code-error">{jsonError}</small> : null}</div>
}

export default function RequestEditor({ method, activeTab, value, onChange, loading = false }: { method: string; activeTab: string; value: RequestEditorValue; onChange: (value: RequestEditorValue) => void; loading?: boolean }) {
  const isGet = method.toUpperCase() === 'GET'
  if (loading) return <div className="editor-panel"><div className="editor-note">Loading request...</div></div>
  if (activeTab === 'Authorization') return <AuthorizationEditor value={value.authorization || { type: 'none' }} onChange={authorization => onChange(patchValue(value, { authorization }))} />
  if (activeTab === 'Headers') return <div className="editor-panel"><div className="editor-heading"><div><strong>Request headers</strong><span>Define metadata sent with the request.</span></div></div><EditorTable kind="header" rows={value.headers} onChange={headers => onChange(patchValue(value, { headers }))} /></div>
  if (activeTab === 'Body') return <BodyEditor value={value} onChange={onChange} disabled={isGet} />
  if (activeTab === 'Scripts') return <div className="editor-panel script-editor"><div className="editor-mode-tabs"><button className="active">Pre-request</button><button>Tests</button></div><textarea aria-label="Request script" placeholder="// Add a script for this request..." spellCheck={false} /></div>
  if (activeTab === 'Settings') return <div className="editor-panel settings-editor"><label><input type="checkbox" checked={value.follow_redirects} onChange={event => onChange(patchValue(value, { follow_redirects: event.target.checked }))} /> Follow redirects</label><label><input type="checkbox" checked={value.verify_ssl} onChange={event => onChange(patchValue(value, { verify_ssl: event.target.checked }))} /> Verify SSL</label><label>Timeout <input type="number" min={1} max={300} value={value.timeout} onChange={event => onChange(patchValue(value, { timeout: Number(event.target.value) || 30 }))} /></label></div>
  return <div className="editor-panel"><div className="editor-heading"><div><strong>Query parameters</strong><span>Parameters are appended to the request URL.</span></div></div><EditorTable kind="parameter" rows={value.query_parameters} onChange={query_parameters => onChange(patchValue(value, { query_parameters }))} /></div>
}
