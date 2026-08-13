import { Plus, Send, Sparkles, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import RequestEditor from '../../RequestEditor'
import type { EnvironmentSummary, CollectionSummary, ExecutionResult, RequestDraft, RequestItem } from '../../types/api'
import { UrlSyntaxLayer } from './UrlSyntaxLayer'
import { ResponsePanel } from './ResponsePanel'
import { EnvironmentPanel } from './EnvironmentPanel'
import { HistoryPanel } from './HistoryPanel'

type RequestWorkspaceProps = {
  tabs: { tabId: string; name: string; dirty: boolean }[]
  activeEditorTabId: string | null
  onSelectTab: (tabId: string) => void
  onCloseTab: (tabId: string) => void
  draft: RequestDraft
  requests: RequestItem[]
  collections: CollectionSummary[]
  environments: EnvironmentSummary[]
  loading: boolean
  working: boolean
  dirty: boolean
  error: string
  activeNav: string
  activeTab: string
  editorLoading: boolean
  sent: ExecutionResult | null
  onDraftChange: (draft: RequestDraft) => void
  onActiveTabChange: (tab: string) => void
  onNewRequest: () => void
  onOpenRequest: (request: RequestItem) => void
  onSave: () => void
  onSend: () => void
  onClearResponse: () => void
  onClearConsole: () => void
  onRefresh: () => void
  onSelectHistory?: (id: string) => void
}

const tabs = ['Params', 'Authorization', 'Headers', 'Body', 'Scripts', 'Settings']

export function RequestWorkspace({
  tabs: editorTabs,
  activeEditorTabId,
  onSelectTab,
  onCloseTab,
  draft,
  requests,
  collections,
  environments,
  loading,
  working,
  dirty,
  error,
  activeNav,
  activeTab,
  editorLoading,
  sent,
  onDraftChange,
  onActiveTabChange,
  onNewRequest,
  onOpenRequest,
  onSave,
  onSend,
  onClearResponse,
  onClearConsole,
  onRefresh,
  onSelectHistory
}: RequestWorkspaceProps) {
  const [editingName, setEditingName] = useState(false)
  const nameInputRef = useRef<HTMLInputElement>(null)
  const setName = (name: string) => onDraftChange({ ...draft, name })
  const setMethod = (method: string) => onDraftChange({ ...draft, method })
  const setUrl = (url: string) => onDraftChange({ ...draft, url })

  useEffect(() => {
    if (editingName) nameInputRef.current?.focus()
  }, [editingName])

  const showBuilder = activeNav === 'Collections' || activeNav === 'AI Assistant' || !activeNav

  return <main className="main-panel">
    {showBuilder && (
      <>
        <div className="request-tabs">
          {editorTabs.map(tab => (
            <button 
              key={tab.tabId} 
              className={`request-tab ${activeEditorTabId === tab.tabId ? 'active' : ''}`}
              onClick={() => onSelectTab(tab.tabId)}
            >
              {tab.name || 'Untitled request'} 
              {tab.dirty && <span style={{ color: 'var(--accent)', marginLeft: '4px', fontSize: '18px', lineHeight: '0' }}>•</span>}
              <X 
                size={13} 
                onClick={(e) => { e.stopPropagation(); onCloseTab(tab.tabId); }} 
                style={{ marginLeft: tab.dirty ? '4px' : 'auto' }}
              />
            </button>
          ))}
          <button className="add-tab" onClick={onNewRequest}><Plus size={16}/></button>
        </div>
    <section className="builder">
      <div className="builder-toolbar">
        <div className="crumb">
          Workspace <span>/</span> 
          <select 
            value={draft.collection_id || ''} 
            onChange={e => onDraftChange({ ...draft, collection_id: e.target.value || null })}
            aria-label="Request collection"
            style={{ background: 'transparent', border: 'none', fontSize: 'inherit', color: 'inherit', outline: 'none', cursor: 'pointer', padding: '0 4px', maxWidth: '150px', textOverflow: 'ellipsis' }}
          >
            <option value="">No collection</option>
            {collections.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          <span>/</span> 
          <span className="crumb-name-wrap">{editingName ? <input ref={nameInputRef} value={draft.name} onChange={event => setName(event.target.value)} onBlur={() => { setEditingName(false); if (dirty && !working) onSave(); }} onKeyDown={event => { if (event.key === 'Enter') { setEditingName(false); if (dirty && !working) onSave(); } else if (event.key === 'Escape') setEditingName(false); }} aria-label="Request name" /> : <strong className="crumb-name" role="button" tabIndex={0} onClick={() => setEditingName(true)} onKeyDown={event => { if (event.key === 'Enter') setEditingName(true) }} title="Click to edit request name">{draft.name || 'Untitled request'}</strong>}</span>
        </div>
        <div className="toolbar-actions"><button className="quiet-button">Import cURL</button><button className="quiet-button"><Sparkles size={14}/> AI Generate</button><button className="primary-button" onClick={onSend} disabled={working}><Send size={14}/> {working ? 'Sending…' : 'Send'}</button></div>
      </div>
      <div className="request-line">
        <select value={draft.method} onChange={event => setMethod(event.target.value)} aria-label="HTTP method" className={`method-select method-${draft.method.toLowerCase()}`}><option>GET</option><option>POST</option><option>PUT</option><option>PATCH</option><option>DELETE</option></select>
        <UrlSyntaxLayer value={draft.url}/>
        <input value={draft.url} onChange={event => setUrl(event.target.value)} aria-label="Request URL" placeholder="https://api.example.com/users" className={draft.url ? 'url-syntax-input' : ''}/>
        <button className="save-button" onClick={onSave} disabled={working}>{working ? 'Saving...' : dirty ? 'Save *' : 'Saved'}</button>
      </div>
      <div className="section-tabs">{tabs.map(tab => <button key={tab} className={`section-tab ${tab === 'Settings' ? 'settings-tab' : ''} ${activeTab === tab ? 'active' : ''}`} onClick={() => onActiveTabChange(tab)}>{tab}</button>)}</div>
      {error && <div className="auth-error" role="alert">{error}</div>}
      <div className="editor-host">
        <RequestEditor method={draft.method} activeTab={activeTab} value={draft.editor} onChange={editor => onDraftChange({ ...draft, editor })} loading={editorLoading} />
      </div>
        <ResponsePanel sent={sent} loading={loading} onClear={onClearResponse} onClearConsole={onClearConsole} />
      </section>
      {activeNav === 'Collections' && <div className="workspace-data-list">{requests.map(item => <button key={item.id} onClick={() => onOpenRequest(item)}><b>{item.method}</b> {item.name}<small>{item.url}</small></button>)}</div>}
    </>
    )}
    {activeNav === 'Environments' && (
      <EnvironmentPanel environments={environments} onRefresh={onRefresh} />
    )}
    {activeNav === 'History' && (
      <HistoryPanel 
        collections={collections}
        environments={environments}
        onSelect={onSelectHistory} 
      />
    )}
  </main>
}
