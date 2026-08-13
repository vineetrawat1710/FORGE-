import { useMemo, useState, useRef, useEffect } from 'react'
import { Info, ArrowRight, CheckCircle2, AlertTriangle, XCircle, ChevronRight, ChevronDown } from 'lucide-react'
import type { ExecutionResult, ConsoleLog } from '../../types/api'

type ResponsePanelProps = {
  sent: ExecutionResult | null
  loading: boolean
  onClear: () => void
  onClearConsole?: () => void
}

type ResponseTab = 'Pretty' | 'Raw' | 'Headers' | 'Cookies' | 'Timeline' | 'Console'

const responseTabs: ResponseTab[] = ['Pretty', 'Raw', 'Headers', 'Cookies', 'Timeline', 'Console']

const LogIcon = ({ level }: { level: string }) => {
  switch (level) {
    case 'INFO': return <Info size={14} style={{ color: 'var(--text-muted)' }} />
    case 'REQUEST': return <ArrowRight size={14} style={{ color: 'var(--text-muted)' }} />
    case 'SUCCESS': return <CheckCircle2 size={14} style={{ color: 'var(--success, #4CAF50)' }} />
    case 'WARNING': return <AlertTriangle size={14} style={{ color: 'var(--warning, #FFC107)' }} />
    case 'ERROR': return <XCircle size={14} style={{ color: 'var(--error, #F44336)' }} />
    default: return <Info size={14} style={{ color: 'var(--text-muted)' }} />
  }
}

const ConsoleRow = ({ log, expanded, toggle }: { log: ConsoleLog, expanded: boolean, toggle: () => void }) => {
  const time = new Date(log.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
  
  return (
    <div style={{ display: 'flex', flexDirection: 'column', borderBottom: '1px solid var(--border)', padding: '8px 0' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px', fontSize: '13px', fontFamily: 'monospace' }}>
        <span style={{ color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{time}</span>
        <span style={{ paddingTop: '2px' }}><LogIcon level={log.level} /></span>
        <span style={{ flex: 1, color: log.level === 'ERROR' ? 'var(--error, #F44336)' : 'var(--text)', wordBreak: 'break-all' }}>{log.message}</span>
        {log.details && (
          <button className="icon-button" onClick={toggle} style={{ padding: '2px' }}>
            {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
        )}
      </div>
      {expanded && log.details && (
        <div style={{ marginTop: '8px', marginLeft: '66px', padding: '12px', background: 'var(--surface-sunken)', borderRadius: '6px', fontSize: '12px', fontFamily: 'monospace', color: 'var(--text-muted)', whiteSpace: 'pre-wrap', wordBreak: 'break-all', border: '1px solid var(--border)' }}>
          {log.details}
        </div>
      )}
    </div>
  )
}

export function ResponsePanel({ sent, loading, onClear, onClearConsole }: ResponsePanelProps) {
  const [activeTab, setActiveTab] = useState<ResponseTab>('Pretty')
  const [expandedLogs, setExpandedLogs] = useState<Set<number>>(new Set())
  const consoleEndRef = useRef<HTMLDivElement>(null)
  
  const size = new Blob([sent?.body || '']).size
  const statusCode = sent?.status_code ?? 'Error'
  const statusText = sent?.reason_phrase || sent?.status_text || ''
  const duration = sent ? `${Math.round(sent.duration_ms || 0)} ms` : ''
  const bytes = sent ? `${size} B` : ''
  const statusClass = typeof statusCode === 'number' && statusCode >= 200 && statusCode < 300 ? 'success' : 'error'

  const prettyBody = useMemo(() => {
    const body = sent?.body || sent?.error || 'Empty response'
    try {
      return JSON.stringify(JSON.parse(body || ''), null, 2)
    } catch {
      return body
    }
  }, [sent])

  useEffect(() => {
    if (activeTab === 'Console' && consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [sent?.console_logs, activeTab])

  const toggleLog = (index: number) => {
    const newExpanded = new Set(expandedLogs)
    if (newExpanded.has(index)) {
      newExpanded.delete(index)
    } else {
      newExpanded.add(index)
    }
    setExpandedLogs(newExpanded)
  }

  const toggleAllLogs = () => {
    if (expandedLogs.size > 0) {
      setExpandedLogs(new Set())
    } else if (sent?.console_logs) {
      const all = new Set(sent.console_logs.map((_, i) => i))
      setExpandedLogs(all)
    }
  }

  const renderContent = () => {
    if (!sent) return null

    if (activeTab === 'Pretty') {
      return <div>
        <div className="response-view-note">Formatted JSON view — readable, indented output.</div>
        <pre className="json-response pretty">{prettyBody}</pre>
      </div>
    }

    if (activeTab === 'Raw') {
      const rawText = sent.body || sent.error || 'Empty response'
      const rawLines = rawText.split('\n')
      return <div>
        <div className="response-view-note">Raw response body — exactly as received from the server.</div>
        <div className="raw-response">
          {rawLines.map((line, index) => <div key={index} className="raw-response-line"><span className="raw-response-line-number">{index + 1}</span><span className="raw-response-line-text">{line || '\u00a0'}</span></div>)}
        </div>
      </div>
    }

    if (activeTab === 'Headers') {
      const headers = Object.entries(sent.headers || {})
      if (!headers.length) return <div className="response-empty">No headers returned.</div>
      return <div className="response-details">{headers.map(([key, value]) => <div key={key} className="response-detail-row"><span>{key}</span><span>{value}</span></div>)}</div>
    }

    if (activeTab === 'Cookies') {
      const cookies = Object.entries(sent.cookies || {})
      if (!cookies.length) return <div className="response-empty">No cookies returned.</div>
      return <div className="response-details">{cookies.map(([key, value]) => <div key={key} className="response-detail-row"><span>{key}</span><span>{value}</span></div>)}</div>
    }
    
    if (activeTab === 'Console') {
      if (!sent.console_logs || sent.console_logs.length === 0) {
        return <div className="response-empty">
          <strong style={{ display: 'block', marginBottom: '8px' }}>No activity yet</strong>
          <span>Run a request to see execution details.</span>
        </div>
      }
      
      return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', paddingBottom: '12px', borderBottom: '1px solid var(--border)' }}>
            <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-muted)' }}>Console</span>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button className="quiet-button" onClick={toggleAllLogs} style={{ fontSize: '12px' }}>
                {expandedLogs.size > 0 ? 'Collapse All' : 'Expand All'}
              </button>
              <button className="quiet-button" onClick={onClearConsole} style={{ fontSize: '12px' }}>Clear</button>
            </div>
          </div>
          <div style={{ flex: 1, overflowY: 'auto', paddingRight: '8px' }}>
            {sent.console_logs.map((log, index) => (
              <ConsoleRow key={index} log={log} expanded={expandedLogs.has(index)} toggle={() => toggleLog(index)} />
            ))}
            <div ref={consoleEndRef} />
          </div>
        </div>
      )
    }

    return <div className="response-empty">No data available for {activeTab.toLowerCase()}.</div>
  }

  return <>
    <div className="response-header">
      <div>
        <span className="eyebrow">Response</span>
        <span className="response-meta">
          <span className={`response-status ${sent ? statusClass : ''}`}>
            <strong>Status</strong>
            <span>{statusCode}{statusText ? ` ${statusText}` : ''}</span>
          </span>
          {sent ? <span className="response-metric"><strong>Time</strong><span>{duration}</span></span> : null}
          {sent ? <span className="response-metric"><strong>Size</strong><span>{bytes}</span></span> : null}
        </span>
      </div>
      <button className="quiet-button" onClick={onClear}>Clear</button>
      <div className="response-tabs">{responseTabs.map(label => <button key={label} type="button" className={label === activeTab ? 'active' : ''} onClick={() => setActiveTab(label)}>{label}</button>)}</div>
    </div>
    <div className="response-view-label">{activeTab} view</div>
    <div className="response-viewer" style={activeTab === 'Console' ? { padding: '16px 24px', overflow: 'hidden', display: 'flex', flexDirection: 'column' } : undefined}>
      {sent ? renderContent() : (
        activeTab === 'Console' ? (
          <div className="empty-response" style={{ gap: '8px' }}>
            <strong>No activity yet</strong>
            <span>Run a request to see execution details.</span>
          </div>
        ) : (
          <div className="empty-response">
            <span className="response-symbol">→</span>
            <strong>{loading ? 'Loading workspace…' : 'No response yet'}</strong>
            <span>Execute a request to inspect:</span>
          </div>
        )
      )}
    </div>
  </>
}
