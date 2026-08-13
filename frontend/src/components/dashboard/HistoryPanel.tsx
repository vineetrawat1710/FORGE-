import { Clock3, RefreshCw, Search, Filter, ExternalLink, ChevronLeft, ChevronRight, ChevronDown, X, FileText } from 'lucide-react'
import { useEffect, useState, useRef } from 'react'
import { api } from '../../api'
import type { EnvironmentSummary, CollectionSummary } from '../../types/api'

export function HistoryPanel({ 
  collections = [], 
  environments = [],
  onSelect 
}: { 
  collections?: CollectionSummary[], 
  environments?: EnvironmentSummary[],
  onSelect?: (id: string) => void 
}) {
  const [history, setHistory] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  
  // Filter state
  const [search, setSearch] = useState('')
  const [methods, setMethods] = useState<string[]>([])
  const [statusClasses, setStatusClasses] = useState<string[]>([])
  const [environmentId, setEnvironmentId] = useState<string>('all')
  const [collectionId, setCollectionId] = useState<string>('all')
  const [responseTime, setResponseTime] = useState<string>('any')
  const [dateRange, setDateRange] = useState<string>('any')
  
  const [filtersOpen, setFiltersOpen] = useState(false)
  
  const popoverRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(event.target as Node)) {
        setFiltersOpen(false)
      }
    }
    if (filtersOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [filtersOpen])

  const loadHistory = () => {
    setLoading(true)
    setError('')
    
    // Process response time
    let duration_min, duration_max
    if (responseTime === '<100') { duration_max = 100 }
    else if (responseTime === '100-500') { duration_min = 100; duration_max = 500 }
    else if (responseTime === '500-1000') { duration_min = 500; duration_max = 1000 }
    else if (responseTime === '>1000') { duration_min = 1000 }
    
    // Process date
    let date_min
    const now = new Date()
    if (dateRange === 'today') {
      date_min = new Date(now.setHours(0, 0, 0, 0)).toISOString()
    } else if (dateRange === '7days') {
      date_min = new Date(now.setDate(now.getDate() - 7)).toISOString()
    } else if (dateRange === '30days') {
      date_min = new Date(now.setDate(now.getDate() - 30)).toISOString()
    }

    const params: any = { limit: 10, page: page }
    if (search) params.search = search
    if (methods.length > 0) params.methods = methods
    if (statusClasses.length > 0) params.status_classes = statusClasses
    if (environmentId !== 'all') params.environment_id = environmentId
    if (collectionId !== 'all') params.collection_id = collectionId
    if (duration_min) params.duration_min = duration_min
    if (duration_max) params.duration_max = duration_max
    if (date_min) params.date_min = date_min

    api.history.list(params).then((data: any) => {
      setHistory(data.items || [])
      setTotal(data.total || data.items?.length || 0)
    }).catch(err => {
      setError(err.message)
    }).finally(() => {
      setLoading(false)
    })
  }

  useEffect(() => {
    loadHistory()
  }, [search, methods, statusClasses, environmentId, collectionId, responseTime, dateRange, page])

  const toggleMethod = (m: string) => setMethods(prev => prev.includes(m) ? prev.filter(x => x !== m) : [...prev, m])
  const toggleStatus = (s: string) => setStatusClasses(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s])

  const removeFilter = (type: string, val?: string) => {
    if (type === 'method' && val) toggleMethod(val)
    if (type === 'status' && val) toggleStatus(val)
    if (type === 'env') setEnvironmentId('all')
    if (type === 'col') setCollectionId('all')
    if (type === 'time') setResponseTime('any')
    if (type === 'date') setDateRange('any')
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%', padding: '24px 32px' }}>
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 600, color: 'var(--text)' }}>History</h2>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div style={{ display: 'flex', gap: '12px', position: 'relative' }}>
          <div style={{ position: 'relative', width: '240px' }}>
            <Search size={14} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input 
              type="text" 
              placeholder="Search history..." 
              value={search}
              onChange={e => setSearch(e.target.value)}
              style={{ width: '100%', padding: '8px 12px 8px 36px', borderRadius: '6px', border: '1px solid var(--border)', background: 'transparent', color: 'var(--text)', fontSize: '13px' }}
            />
          </div>
          <button 
            onClick={() => setFiltersOpen(!filtersOpen)}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px', borderRadius: '6px', border: '1px solid var(--border)', background: filtersOpen ? 'var(--surface-sunken)' : 'transparent', color: 'var(--text)', fontSize: '13px', cursor: 'pointer' }}
          >
            <Filter size={14} /> Filters
          </button>
          
          {filtersOpen && (
            <div ref={popoverRef} style={{ position: 'absolute', top: '100%', left: '252px', marginTop: '8px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px', boxShadow: '0 10px 30px rgba(0,0,0,0.2)', width: '600px', zIndex: 100, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Filter History
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1px', background: 'var(--border)' }}>
                <div style={{ background: 'var(--surface)', padding: '16px' }}>
                  <div style={{ fontSize: '12px', fontWeight: 600, marginBottom: '12px' }}>Method</div>
                  {['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map(m => (
                    <label key={m} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', fontSize: '13px', cursor: 'pointer' }}>
                      <input type="checkbox" checked={methods.includes(m)} onChange={() => toggleMethod(m)} /> {m}
                    </label>
                  ))}
                  
                  <div style={{ fontSize: '12px', fontWeight: 600, marginBottom: '12px', marginTop: '24px' }}>Status</div>
                  {['2xx', '3xx', '4xx', '5xx', 'failed'].map(s => (
                    <label key={s} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', fontSize: '13px', cursor: 'pointer' }}>
                      <input type="checkbox" checked={statusClasses.includes(s)} onChange={() => toggleStatus(s)} /> {s === 'failed' ? 'Failed' : s}
                    </label>
                  ))}
                </div>
                
                <div style={{ background: 'var(--surface)', padding: '16px' }}>
                  <div style={{ fontSize: '12px', fontWeight: 600, marginBottom: '12px' }}>Environment</div>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', fontSize: '13px', cursor: 'pointer' }}>
                    <input type="radio" checked={environmentId === 'all'} onChange={() => setEnvironmentId('all')} /> All
                  </label>
                  {environments.map(e => (
                    <label key={e.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', fontSize: '13px', cursor: 'pointer' }}>
                      <input type="radio" checked={environmentId === e.id} onChange={() => setEnvironmentId(e.id)} /> {e.name}
                    </label>
                  ))}

                  <div style={{ fontSize: '12px', fontWeight: 600, marginBottom: '12px', marginTop: '24px' }}>Collection</div>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', fontSize: '13px', cursor: 'pointer' }}>
                    <input type="radio" checked={collectionId === 'all'} onChange={() => setCollectionId('all')} /> All
                  </label>
                  {collections.map(c => (
                    <label key={c.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', fontSize: '13px', cursor: 'pointer' }}>
                      <input type="radio" checked={collectionId === c.id} onChange={() => setCollectionId(c.id)} /> {c.name}
                    </label>
                  ))}
                </div>
                
                <div style={{ background: 'var(--surface)', padding: '16px' }}>
                  <div style={{ fontSize: '12px', fontWeight: 600, marginBottom: '12px' }}>Response time</div>
                  {[
                    { val: 'any', label: 'Any' },
                    { val: '<100', label: '<100ms' },
                    { val: '100-500', label: '100–500ms' },
                    { val: '500-1000', label: '500ms–1s' },
                    { val: '>1000', label: '>1s' }
                  ].map(t => (
                    <label key={t.val} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', fontSize: '13px', cursor: 'pointer' }}>
                      <input type="radio" checked={responseTime === t.val} onChange={() => setResponseTime(t.val)} /> {t.label}
                    </label>
                  ))}

                  <div style={{ fontSize: '12px', fontWeight: 600, marginBottom: '12px', marginTop: '24px' }}>Date</div>
                  {[
                    { val: 'any', label: 'Any time' },
                    { val: 'today', label: 'Today' },
                    { val: '7days', label: 'Last 7 days' },
                    { val: '30days', label: 'Last 30 days' }
                  ].map(d => (
                    <label key={d.val} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', fontSize: '13px', cursor: 'pointer' }}>
                      <input type="radio" checked={dateRange === d.val} onChange={() => setDateRange(d.val)} /> {d.label}
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '13px', color: 'var(--text-muted)' }}>
          <span>{total === 0 ? 0 : (page - 1) * 10 + 1}–{Math.min(page * 10, total)} of {total}</span>
          <div style={{ display: 'flex', gap: '4px' }}>
            <button className="icon-button" disabled={page === 1} onClick={() => setPage(page - 1)} style={{ padding: '4px', opacity: page === 1 ? 0.5 : 1, cursor: page === 1 ? 'not-allowed' : 'pointer' }}><ChevronLeft size={16}/></button>
            <button className="icon-button" disabled={page === (Math.ceil(total / 10) || 1)} onClick={() => setPage(page + 1)} style={{ padding: '4px', opacity: page === (Math.ceil(total / 10) || 1) ? 0.5 : 1, cursor: page === (Math.ceil(total / 10) || 1) ? 'not-allowed' : 'pointer' }}><ChevronRight size={16}/></button>
          </div>
          <button className="icon-button" onClick={loadHistory} disabled={loading} style={{ padding: '4px' }}>
            <RefreshCw size={14} className={loading ? 'spinning' : ''}/>
          </button>
        </div>
      </div>
      
      {(methods.length > 0 || statusClasses.length > 0 || environmentId !== 'all' || collectionId !== 'all' || responseTime !== 'any' || dateRange !== 'any') && (
        <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginRight: '8px' }}>Active:</span>
          {methods.map(m => (
            <div key={`m-${m}`} style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'var(--surface-sunken)', padding: '4px 8px', borderRadius: '12px', fontSize: '12px', border: '1px solid var(--border)' }}>
              {m} <X size={12} style={{ cursor: 'pointer', color: 'var(--text-muted)' }} onClick={() => removeFilter('method', m)} />
            </div>
          ))}
          {statusClasses.map(s => (
            <div key={`s-${s}`} style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'var(--surface-sunken)', padding: '4px 8px', borderRadius: '12px', fontSize: '12px', border: '1px solid var(--border)' }}>
              {s === 'failed' ? 'Failed' : s} <X size={12} style={{ cursor: 'pointer', color: 'var(--text-muted)' }} onClick={() => removeFilter('status', s)} />
            </div>
          ))}
          {environmentId !== 'all' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'var(--surface-sunken)', padding: '4px 8px', borderRadius: '12px', fontSize: '12px', border: '1px solid var(--border)' }}>
              Env: {environments.find(e => e.id === environmentId)?.name || 'Unknown'} <X size={12} style={{ cursor: 'pointer', color: 'var(--text-muted)' }} onClick={() => removeFilter('env')} />
            </div>
          )}
          {collectionId !== 'all' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'var(--surface-sunken)', padding: '4px 8px', borderRadius: '12px', fontSize: '12px', border: '1px solid var(--border)' }}>
              Col: {collections.find(c => c.id === collectionId)?.name || 'Unknown'} <X size={12} style={{ cursor: 'pointer', color: 'var(--text-muted)' }} onClick={() => removeFilter('col')} />
            </div>
          )}
          {responseTime !== 'any' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'var(--surface-sunken)', padding: '4px 8px', borderRadius: '12px', fontSize: '12px', border: '1px solid var(--border)' }}>
              Time: {responseTime} <X size={12} style={{ cursor: 'pointer', color: 'var(--text-muted)' }} onClick={() => removeFilter('time')} />
            </div>
          )}
          {dateRange !== 'any' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', background: 'var(--surface-sunken)', padding: '4px 8px', borderRadius: '12px', fontSize: '12px', border: '1px solid var(--border)' }}>
              Date: {dateRange} <X size={12} style={{ cursor: 'pointer', color: 'var(--text-muted)' }} onClick={() => removeFilter('date')} />
            </div>
          )}
        </div>
      )}

      {error && <div className="auth-error" style={{ marginBottom: '16px' }}>{error}</div>}

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        {/* Table Header */}
        <div style={{ display: 'grid', gridTemplateColumns: '60px 1fr 60px 80px 80px 100px 80px 100px 100px', gap: '12px', padding: '12px 16px', borderBottom: '1px solid var(--border)', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', borderTop: '1px solid var(--border)' }}>
          <div>Method</div>
          <div>URL</div>
          <div>Status</div>
          <div>Duration</div>
          <div>Size</div>
          <div>Environment</div>
          <div style={{ textAlign: 'center' }}>Detail</div>
          <div>Date &darr;</div>
          <div>Time</div>
        </div>

        {/* Table Body */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {loading && history.length === 0 ? (
            <div style={{ padding: '24px', fontSize: '13px', color: 'var(--text-muted)', textAlign: 'center' }}>Loading history...</div>
          ) : history.length === 0 ? (
            <div style={{ padding: '24px', fontSize: '13px', color: 'var(--text-muted)', textAlign: 'center' }}>No execution history found.</div>
          ) : (
            history.map((item, idx) => {
              const success = item.status_code >= 200 && item.status_code < 300
              const d = new Date(item.executed_at)
              
              const dateStr = d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
              const timeStr = d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
              
              const envName = environments.find(e => e.id === item.environment_id)?.name || '--'
              
              const methodColor: Record<string, string> = {
                get: 'var(--syntax-get, #347043)',
                post: 'var(--syntax-post, #A56A22)',
                put: 'var(--syntax-put, #3E6DA8)',
                patch: 'var(--syntax-patch, #6c5ce7)',
                delete: 'var(--syntax-delete, #B34C3F)',
              }
              const color = methodColor[item.method?.toLowerCase() || ''] || 'var(--text)'
              
              return (
                <div key={idx} onClick={() => onSelect && onSelect(item.id)} style={{ display: 'grid', gridTemplateColumns: '60px 1fr 60px 80px 80px 100px 80px 100px 100px', gap: '12px', padding: '12px 16px', borderBottom: '1px solid var(--border)', fontSize: '13px', alignItems: 'center', cursor: 'pointer' }} className="history-row">
                  <b style={{ color: color, fontSize: '11px', fontFamily: 'var(--font-mono, monospace)' }}>{item.method}</b>
                  <span style={{ fontFamily: 'var(--font-mono, monospace)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.url}</span>
                  <span style={{ color: success ? 'var(--syntax-get, #347043)' : (item.status_code ? 'var(--syntax-delete, #B34C3F)' : 'var(--text-muted)'), fontWeight: success ? 600 : 400 }}>{item.status_code || '--'}</span>
                  <span style={{ color: 'var(--text)' }}>{Math.round(item.duration_ms)} ms</span>
                  <span style={{ color: 'var(--text)' }}>{item.response_size != null ? `${(item.response_size / 1024).toFixed(1)} KB` : '--'}</span>
                  <span style={{ color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{envName}</span>
                  <div style={{ display: 'flex', justifyContent: 'center' }}>
                    <button className="icon-button" style={{ padding: '4px' }} onClick={(e) => { e.stopPropagation(); onSelect && onSelect(item.id) }}><FileText size={14} /></button>
                  </div>
                  <span style={{ color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{dateStr}</span>
                  <span style={{ color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{timeStr}</span>
                </div>
              )
            })
          )}
        </div>

        {/* Footer Pagination */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 0', marginTop: 'auto' }}>
          <div /> {/* Spacer */}
          <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
            <button className="icon-button" disabled={page === 1} onClick={() => setPage(page - 1)} style={{ padding: '6px', border: '1px solid var(--border)', borderRadius: '4px', opacity: page === 1 ? 0.5 : 1, cursor: page === 1 ? 'not-allowed' : 'pointer' }}><ChevronLeft size={16}/></button>
            {Array.from({ length: Math.ceil(total / 10) || 1 }, (_, i) => i + 1).filter(p => p === 1 || p === Math.ceil(total / 10) || Math.abs(p - page) <= 2).map((p, i, arr) => (
              <div key={p} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                {i > 0 && p - arr[i - 1] > 1 && <span style={{ padding: '4px 8px', color: 'var(--text-muted)' }}>...</span>}
                <button onClick={() => setPage(p)} style={{ padding: '4px 12px', border: p === page ? '1px solid var(--border)' : 'none', borderRadius: '4px', background: p === page ? 'var(--surface-sunken)' : 'transparent', color: 'var(--text)', fontSize: '13px', fontWeight: p === page ? 600 : 400, cursor: 'pointer' }}>{p}</button>
              </div>
            ))}
            <button className="icon-button" disabled={page === (Math.ceil(total / 10) || 1)} onClick={() => setPage(page + 1)} style={{ padding: '6px', border: '1px solid var(--border)', borderRadius: '4px', opacity: page === (Math.ceil(total / 10) || 1) ? 0.5 : 1, cursor: page === (Math.ceil(total / 10) || 1) ? 'not-allowed' : 'pointer' }}><ChevronRight size={16}/></button>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: 'var(--text-muted)' }}>
            10 / page <ChevronDown size={14} />
          </div>
        </div>
      </div>
      
      <style>{`
        .history-row:hover {
          background: rgba(100, 100, 100, 0.05);
        }
      `}</style>
    </div>
  )
}
