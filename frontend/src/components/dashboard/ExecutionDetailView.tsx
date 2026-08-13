import { ArrowLeft, Play, Plus, Clock3, Trash2 } from 'lucide-react'
import { useEffect, useState, useMemo } from 'react'
import { api } from '../../api'
import type { EnvironmentSummary, ExecutionResult } from '../../types/api'

import React, { ErrorInfo, ReactNode } from 'react'

class ErrorBoundary extends React.Component<{children: ReactNode}, {hasError: boolean, error: Error | null}> {
  constructor(props: {children: ReactNode}) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ExecutionDetailView caught error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '24px', color: 'var(--error-dark, red)', background: 'var(--surface)' }}>
          <h2>Something went wrong in ExecutionDetailView.</h2>
          <pre>{this.state.error?.toString()}</pre>
          <pre style={{ fontSize: '12px', marginTop: '16px' }}>{this.state.error?.stack}</pre>
        </div>
      );
    }
    return this.props.children; 
  }
}

type ExecutionDetailViewProps = {
  historyId: string
  environments: EnvironmentSummary[]
  onBack: () => void
  onOpenAsNewRequest: (snapshot: any) => void
  onReplay: (snapshot: any, envId: string | null) => void
}

export function ExecutionDetailView({ historyId, environments, onBack, onOpenAsNewRequest, onReplay }: ExecutionDetailViewProps) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [data, setData] = useState<any>(null)
  const [requestTab, setRequestTab] = useState<'Params' | 'Headers' | 'Authorization' | 'Body'>('Params')
  const [responseTab, setResponseTab] = useState<'Pretty' | 'Raw' | 'Headers' | 'Cookies' | 'Timeline'>('Pretty')

  useEffect(() => {
    setLoading(true)
    setError('')
    api.history.get(historyId).then((res: any) => {
      setData(res)
    }).catch(err => {
      setError(err.message || 'Failed to load execution detail')
    }).finally(() => {
      setLoading(false)
    })
  }, [historyId])

  const maskSecret = (val: string | undefined | null) => {
    if (!val) return ''
    return '••••••••••••••••'
  }

  const res = data?.response_snapshot;

  const prettyBody = useMemo(() => {
    if (!res) return ''
    let body = res.body || res.error || 'Empty response'
    if (typeof body !== 'string') {
      try {
        body = JSON.stringify(body)
      } catch {
        body = String(body)
      }
    }
    try {
      return JSON.stringify(JSON.parse(body), null, 2)
    } catch {
      return body
    }
  }, [res])

  const rawText = useMemo(() => {
    if (!res) return ''
    let body = res.body || res.error || 'Empty response'
    if (typeof body !== 'string') {
      try {
        body = JSON.stringify(body)
      } catch {
        body = String(body)
      }
    }
    return body
  }, [res])

  if (loading) {
    return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
      Loading execution detail...
    </div>
  }

  if (error || !data) {
    return <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)', gap: '16px' }}>
      <div className="auth-error">{error || 'Execution not found'}</div>
      <button className="secondary-button" onClick={() => {
        setLoading(true)
        setError('')
        api.history.get(historyId).then((res: any) => setData(res)).catch(err => setError(err.message)).finally(() => setLoading(false))
      }}>Retry</button>
      <button className="secondary-button" onClick={onBack}>Back to History</button>
    </div>
  }

  const { request_snapshot: req } = data
  const success = data.status_code >= 200 && data.status_code < 300
  const d = new Date(data.executed_at)
  
  const envName = (environments || []).find(e => e.id === data.environment_id)?.name || 'No Environment'

  const handleReplay = () => {
    if (data.environment_id && !(environments || []).find(e => e.id === data.environment_id)) {
      alert(`Warning: The environment used for this execution no longer exists. Please select a valid environment from the top navigation before replaying, or open as a new request.`)
      return
    }
    const env = (environments || []).find(e => e.id === data.environment_id)
    if (env && env.name.toLowerCase().includes('prod')) {
      if (!confirm(`You are about to replay a request against a Production environment (${env.name}). Are you sure?`)) {
        return
      }
    }
    onReplay(req, data.environment_id)
  }



  const highlightJson = (json: string) => {
    if (typeof json !== 'string') return null;
    if (!json.startsWith('{') && !json.startsWith('[')) return json;
    
    return json.split('\n').map((line, i) => {
      // Very basic highlight: keys in red, string values in green, numbers/booleans in blue
      let highlighted = line
        .replace(/"([^"]+)":/g, '<span style="color: #d32f2f">"$1"</span>:')
        .replace(/: "([^"]*)"/g, ': <span style="color: #137333">"$1"</span>')
        .replace(/: (true|false|null|\d+)/g, ': <span style="color: #1976d2">$1</span>');
      return <div key={i} dangerouslySetInnerHTML={{ __html: highlighted || '\u00A0' }} />
    });
  }

  return (
    <ErrorBoundary>
      <main className="main-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%', background: 'var(--surface)' }}>
        {/* Top Bar */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 24px', borderBottom: '1px solid var(--border)' }}>
          <button className="secondary-button" onClick={onBack} title="Back to History" style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 12px', fontSize: '13px', fontWeight: 500 }}>
            <ArrowLeft size={16} /> Back to History
          </button>
        
        <div style={{ display: 'flex', gap: '12px' }}>
          <button style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', background: 'transparent', border: '1px solid var(--success-dark, #2b5f3a)', borderRadius: '6px', fontSize: '13px', color: 'var(--success-dark, #2b5f3a)', cursor: 'pointer', fontWeight: 600 }} onClick={() => onOpenAsNewRequest(req)}>
            <Plus size={14} /> Open as new request
          </button>
          <button style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 16px', background: 'var(--success-dark, #2b5f3a)', border: 'none', borderRadius: '6px', fontSize: '13px', color: '#fff', cursor: 'pointer', fontWeight: 600 }} onClick={handleReplay}>
            <Play size={14} fill="currentColor" /> Replay
          </button>
        </div>
      </div>

      {/* Main Split Layout */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        
        {/* Left Column (Request) */}
        <div style={{ width: '50%', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column' }}>
          {/* Sub Header Left */}
          <div style={{ display: 'flex', alignItems: 'center', padding: '16px 24px', borderBottom: '1px solid var(--border)', gap: '16px' }}>
            <span style={{ 
              fontSize: '13px', 
              fontWeight: 700, 
              padding: '4px 8px', 
              borderRadius: '4px', 
              background: 'var(--success-light, #e6f4ea)', 
              color: 'var(--success-dark, #137333)',
              fontFamily: 'var(--font-mono, monospace)'
            }}>
              {req?.method || 'GET'}
            </span>
            <span style={{ fontSize: '15px', color: 'var(--text)', fontWeight: 600 }}>
              {req?.url || ''}
            </span>
          </div>

          <div style={{ padding: '8px 16px 0', borderBottom: '1px solid var(--border)', display: 'flex', gap: '24px', background: 'var(--surface)' }}>
            {['Params', `Headers (${req?.headers?.length || 0})`, 'Authorization', 'Body'].map(tab => {
              const baseTab = tab.split(' ')[0]
              return (
                <button 
                  key={tab} 
                  onClick={() => setRequestTab(baseTab as any)}
                  style={{ background: 'transparent', border: 'none', padding: '8px 4px 12px', fontSize: '13px', color: requestTab === baseTab ? 'var(--text)' : 'var(--text-muted)', fontWeight: requestTab === baseTab ? 600 : 500, borderBottom: requestTab === baseTab ? '2px solid var(--success-dark, #137333)' : '2px solid transparent', cursor: 'pointer' }}
                >
                  {tab}
                </button>
              )
            })}
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
            {requestTab === 'Params' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
                <div>
                  <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text)', marginBottom: '16px' }}>Query Parameters</div>
                  {!req?.query_parameters || !Array.isArray(req.query_parameters) || req.query_parameters.length === 0 ? (
                    <div style={{ color: 'var(--text-muted)', fontSize: '13px', padding: '12px 8px', borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)' }}>No query parameters</div>
                  ) : (
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                      <thead><tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left', color: 'var(--text)' }}><th style={{ padding: '8px', fontWeight: 600, width: '30%' }}>Key</th><th style={{ padding: '8px', fontWeight: 600, width: '30%' }}>Value</th><th style={{ padding: '8px', fontWeight: 600 }}>Description</th></tr></thead>
                      <tbody>
                        {req.query_parameters.map((p: any, i: number) => (
                          <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                            <td style={{ padding: '12px 8px', color: p?.is_active === false ? 'var(--text-muted)' : 'var(--text)' }}>{p?.key}</td>
                            <td style={{ padding: '12px 8px', color: p?.is_active === false ? 'var(--text-muted)' : 'var(--text)' }}>{p?.value}</td>
                            <td style={{ padding: '12px 8px', color: 'var(--text-muted)' }}>{p?.description || ''}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
                <div>
                  <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text)', marginBottom: '16px' }}>Path Parameters</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '13px', padding: '12px 8px', borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)' }}>No path parameters</div>
                </div>
              </div>
            )}
            {requestTab === 'Headers' && (
              <div>
                {!req?.headers || !Array.isArray(req.headers) || req.headers.length === 0 ? (
                  <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>No headers</div>
                ) : (
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                    <thead><tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left', color: 'var(--text-muted)' }}><th style={{ padding: '8px', fontWeight: 600 }}>Key</th><th style={{ padding: '8px', fontWeight: 600 }}>Value</th></tr></thead>
                    <tbody>
                      {req.headers.map((h: any, i: number) => {
                        const isSecret = h?.key?.toLowerCase() === 'authorization' || h?.key?.toLowerCase() === 'cookie' || h?.key?.toLowerCase() === 'x-api-key'
                        return <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}><td style={{ padding: '8px', color: h?.is_active === false ? 'var(--text-muted)' : 'var(--text)' }}>{h?.key}</td><td style={{ padding: '8px', color: h?.is_active === false ? 'var(--text-muted)' : 'var(--text)' }}>{isSecret ? maskSecret(h?.value) : h?.value}</td></tr>
                      })}
                    </tbody>
                  </table>
                )}
              </div>
            )}
            {requestTab === 'Authorization' && (
              <div style={{ fontSize: '13px' }}>
                <div style={{ marginBottom: '12px' }}><b>Type:</b> {req?.authorization?.type || 'none'}</div>
                {req?.authorization?.type === 'bearer' && (
                  <div><b>Token:</b> {maskSecret(req?.authorization?.token)}</div>
                )}
                {req?.authorization?.type === 'basic' && (
                  <div>
                    <div style={{ marginBottom: '4px' }}><b>Username:</b> {req?.authorization?.username}</div>
                    <div><b>Password:</b> {maskSecret(req?.authorization?.password)}</div>
                  </div>
                )}
                {req?.authorization?.type === 'apikey' && (
                  <div>
                    <div style={{ marginBottom: '4px' }}><b>Key:</b> {req?.authorization?.key}</div>
                    <div style={{ marginBottom: '4px' }}><b>Value:</b> {maskSecret(req?.authorization?.value)}</div>
                    <div><b>In:</b> {req?.authorization?.in}</div>
                  </div>
                )}
              </div>
            )}
            {requestTab === 'Body' && (
              <div style={{ fontSize: '13px', height: '100%', display: 'flex', flexDirection: 'column' }}>
                <div style={{ marginBottom: '12px' }}><b>Type:</b> {req?.body_type || 'none'}</div>
                {req?.body_type !== 'none' && (
                  <pre style={{ flex: 1, padding: '12px', background: 'var(--surface-sunken)', border: '1px solid var(--border)', borderRadius: '6px', overflow: 'auto', margin: 0, fontFamily: 'var(--font-mono, monospace)', fontSize: '12px' }}>
                    {req?.body}
                  </pre>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right Column (Response) */}
        <div style={{ width: '50%', display: 'flex', flexDirection: 'column', background: 'var(--surface)' }}>
          {/* Sub Header Right (Metrics) */}
          <div style={{ display: 'flex', alignItems: 'center', padding: '16px 24px', borderBottom: '1px solid var(--border)', gap: '16px' }}>
            <span style={{ 
              fontSize: '12px', 
              fontWeight: 700, 
              padding: '4px 8px', 
              borderRadius: '4px', 
              background: success ? 'var(--success-light, #e6f4ea)' : 'var(--error-light, #fce8e6)', 
              color: success ? 'var(--success-dark, #137333)' : 'var(--error-dark, #c5221f)',
            }}>
              {data.status_code || '--'} {res?.status_text || 'OK'}
            </span>
            
            <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>{Math.round(data.duration_ms)} ms</span>
            <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>{res?.response_size != null ? `${(res.response_size / 1024).toFixed(1)} KB` : '--'}</span>
            <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>•</span>
            <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>{envName}</span>
            <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>•</span>
            <span style={{ fontSize: '13px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Clock3 size={14}/> {isNaN(d.getTime()) ? 'Unknown Date' : d.toLocaleString('en-US', { dateStyle: 'short', timeStyle: 'medium' })}
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 24px', borderBottom: '1px solid var(--border)' }}>
            <span style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text)' }}>Response</span>
            <button style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', background: 'transparent', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '13px', color: 'var(--text)', cursor: 'pointer', fontWeight: 600 }}>
              <Trash2 size={14} /> Clear
            </button>
          </div>
          
          <div style={{ padding: '8px 16px 0', borderBottom: '1px solid var(--border)', display: 'flex', gap: '24px' }}>
            {['Pretty', 'Raw', `Headers (${Object.keys(res?.headers || {}).length})`, `Cookies (${Object.keys(res?.cookies || {}).length})`, 'Timeline'].map(tab => {
              const baseTab = tab.split(' ')[0]
              return (
                <button 
                  key={tab} 
                  onClick={() => setResponseTab(baseTab as any)}
                  style={{ background: 'transparent', border: 'none', padding: '8px 4px 12px', fontSize: '13px', color: responseTab === baseTab ? 'var(--text)' : 'var(--text-muted)', fontWeight: responseTab === baseTab ? 600 : 500, borderBottom: responseTab === baseTab ? '2px solid var(--success-dark, #137333)' : '2px solid transparent', cursor: 'pointer' }}
                >
                  {tab}
                </button>
              )
            })}
          </div>
          
          <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column' }}>
            {responseTab === 'Pretty' && (
              <>
                <div style={{ background: 'var(--success-light, #f1f8f4)', color: 'var(--success-dark, #2b5f3a)', padding: '12px 16px', borderRadius: '6px', fontSize: '13px', fontWeight: 600, marginBottom: '16px', border: '1px solid var(--success, #a3d9b8)' }}>
                  Note: Formatted JSON view — readable, indented output.
                </div>
                <div style={{ flex: 1, background: 'transparent', padding: '16px 0', borderRadius: '6px', fontSize: '13px', display: 'flex' }}>
                  <div style={{ color: 'var(--text-muted)', textAlign: 'right', paddingRight: '16px', userSelect: 'none', opacity: 0.7, fontFamily: 'var(--font-mono, monospace)', lineHeight: '1.6' }}>
                    {typeof prettyBody === 'string' ? prettyBody.split('\n').map((_, i) => <div key={i}>{i + 1}</div>) : null}
                  </div>
                  <pre className="json-response pretty" style={{ margin: 0, padding: 0, flex: 1, overflowX: 'auto', lineHeight: '1.6', wordBreak: 'break-all', whiteSpace: 'pre-wrap', background: 'transparent', fontFamily: 'var(--font-mono, monospace)' }}>
                    {highlightJson(prettyBody)}
                  </pre>
                </div>
              </>
            )}
            {responseTab === 'Raw' && (
              <>
                <div style={{ background: 'var(--success-light, #f1f8f4)', color: 'var(--success-dark, #2b5f3a)', padding: '12px 16px', borderRadius: '6px', fontSize: '13px', fontWeight: 600, marginBottom: '16px', border: '1px solid var(--success, #a3d9b8)' }}>
                  Note: Raw response body — exactly as received from the server.
                </div>
                <div style={{ flex: 1, background: 'transparent', padding: '16px 0', borderRadius: '6px', fontSize: '13px', display: 'flex' }}>
                  <div style={{ color: 'var(--text-muted)', textAlign: 'right', paddingRight: '16px', userSelect: 'none', opacity: 0.7, fontFamily: 'var(--font-mono, monospace)', lineHeight: '1.6' }}>
                    {typeof rawText === 'string' ? rawText.split('\n').map((_, i) => <div key={i}>{i + 1}</div>) : null}
                  </div>
                  <pre className="json-response raw" style={{ margin: 0, padding: 0, flex: 1, overflowX: 'auto', lineHeight: '1.6', wordBreak: 'break-all', whiteSpace: 'pre-wrap', background: 'transparent', fontFamily: 'var(--font-mono, monospace)' }}>
                    {rawText}
                  </pre>
                </div>
              </>
            )}
            {responseTab === 'Headers' && (
              <div>
                {!res?.headers || Object.keys(res.headers).length === 0 ? (
                  <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>No headers returned.</div>
                ) : (
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                    <thead><tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left', color: 'var(--text-muted)' }}><th style={{ padding: '8px', fontWeight: 600, width: '30%' }}>Key</th><th style={{ padding: '8px', fontWeight: 600 }}>Value</th></tr></thead>
                    <tbody>
                      {Object.entries(res.headers).map(([key, value], i) => (
                        <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}><td style={{ padding: '12px 8px', color: 'var(--text)' }}>{key}</td><td style={{ padding: '12px 8px', color: 'var(--text)', wordBreak: 'break-all' }}>{String(value)}</td></tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            )}
            {responseTab === 'Cookies' && (
              <div>
                {!res?.cookies || Object.keys(res.cookies).length === 0 ? (
                  <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>No cookies returned.</div>
                ) : (
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                    <thead><tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left', color: 'var(--text-muted)' }}><th style={{ padding: '8px', fontWeight: 600, width: '30%' }}>Key</th><th style={{ padding: '8px', fontWeight: 600 }}>Value</th></tr></thead>
                    <tbody>
                      {Object.entries(res.cookies).map(([key, value], i) => (
                        <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}><td style={{ padding: '12px 8px', color: 'var(--text)' }}>{key}</td><td style={{ padding: '12px 8px', color: 'var(--text)', wordBreak: 'break-all' }}>{String(value)}</td></tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            )}
            {responseTab === 'Timeline' && (
              <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
                Timeline view is not available for historical snapshots.
              </div>
            )}
          </div>
        </div>
      </div>
      
      {/* Footer */}
      <div style={{ display: 'flex', alignItems: 'center', padding: '16px 24px', borderTop: '1px solid var(--border)', background: 'var(--surface)' }}>
        <div style={{ display: 'flex', gap: '64px' }}>
          <div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px' }}>Request ID</div>
            <div style={{ fontSize: '13px', color: 'var(--text)' }}>{req?.id || 'N/A'}</div>
          </div>
          <div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px' }}>History ID</div>
            <div style={{ fontSize: '13px', color: 'var(--text)' }}>{historyId}</div>
          </div>
          <div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px' }}>Executed by</div>
            <div style={{ fontSize: '13px', color: 'var(--text)' }}>vineet@example.com</div>
          </div>
          <div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px' }}>User Agent</div>
            <div style={{ fontSize: '13px', color: 'var(--text)' }}>API Studio AI/1.0.0</div>
          </div>
        </div>
      </div>
      </main>
    </ErrorBoundary>
  )
}
