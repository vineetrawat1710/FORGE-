import { useCallback, useState } from 'react'
import { AIAssistantPanel } from './components/dashboard/AIAssistantPanel'
import { EnvironmentPanel } from './components/dashboard/EnvironmentPanel'
import { RequestWorkspace } from './components/dashboard/RequestWorkspace'
import { ExecutionDetailView } from './components/dashboard/ExecutionDetailView'
import { TopNavigation } from './components/dashboard/TopNavigation'
import { WorkspaceSidebar } from './components/dashboard/WorkspaceSidebar'
import { useDirtyState, useSaveShortcut } from './hooks/useDirtyState'
import { useRequestEditorState } from './hooks/useRequestEditorState'
import { useWorkspaceData } from './hooks/useWorkspaceData'
import { api } from './api'
import { fingerprint } from './utils/requestSerialization'

export default function DashboardConnected() {
  const [activeNav, setActiveNav] = useState('Collections')
  const [activeTab, setActiveTab] = useState('Params')
  const [aiOpen, setAiOpen] = useState(true)
  const [lightTheme, setLightTheme] = useState(true)
  const [activeHistoryId, setActiveHistoryId] = useState<string | null>(null)
  const [aiConversation, setAiConversation] = useState<{role: 'user' | 'ai', content: string}[]>([])
  const [aiLoading, setAiLoading] = useState(false)
  const workspace = useWorkspaceData()
  const requestEditor = useRequestEditorState(workspace.load, workspace.setError)
  const dirty = useDirtyState(requestEditor.draft, requestEditor.savedFingerprint)

  useSaveShortcut({ dirty, working: requestEditor.working, onSave: requestEditor.save })

  const logout = useCallback(() => {
    localStorage.removeItem('api_studio_access_token')
    localStorage.removeItem('api_studio_refresh_token')
    window.location.reload()
  }, [])

  const askAI = useCallback(async (prompt: string) => {
    if (!prompt.trim() || aiLoading) return
    workspace.setError('')
    setAiLoading(true)
    setAiConversation(prev => [...prev, { role: 'user', content: prompt }])
    try {
      const response = await api.ai.chat({
        message: prompt,
        context_request_id: requestEditor.active?.id,
        context_environment_id: workspace.environments.find(item => item.is_active)?.id,
      })
      setAiConversation(prev => [...prev, { role: 'ai', content: (response as any).reply || 'No response.' }])
    } catch (error) {
      setAiConversation(prev => [...prev, { role: 'ai', content: `Error: ${error instanceof Error ? error.message : 'AI request failed'}` }])
    } finally {
      setAiLoading(false)
    }
  }, [requestEditor.active?.id, workspace.environments, workspace.setError, aiLoading])

  const handleSelectHistory = useCallback((id: string) => {
    setActiveHistoryId(id)
  }, [])

  const handleOpenAsNewRequest = useCallback((snapshot: any) => {
    if (dirty && !confirm('You have unsaved changes. Discard them to open this historical request?')) {
      return
    }
    requestEditor.setDraft({
      ...requestEditor.draft,
      method: snapshot.method || 'GET',
      url: snapshot.url || '',
      editor: {
        ...requestEditor.draft.editor,
        headers: snapshot.headers || [],
        query_parameters: snapshot.query_parameters || [],
        authorization: snapshot.authorization || { type: 'none' },
        body: snapshot.body || '',
        body_type: snapshot.body_type || 'none',
      }
    })
    requestEditor.setSent(null)
    setActiveHistoryId(null)
  }, [dirty, requestEditor])

  const handleReplay = useCallback(async (snapshot: any, envId: string | null, historyId: string) => {
    if (dirty && !confirm('You have unsaved changes. Discard them to replay this historical request?')) {
      return
    }
    
    // We load it into the draft and immediately execute it
    requestEditor.setDraft({
      ...requestEditor.draft,
      method: snapshot.method || 'GET',
      url: snapshot.url || '',
      editor: {
        ...requestEditor.draft.editor,
        headers: snapshot.headers || [],
        query_parameters: snapshot.query_parameters || [],
        authorization: snapshot.authorization || { type: 'none' },
        body: snapshot.body || '',
        body_type: snapshot.body_type || 'none',
      }
    })
    
    workspace.setError('')
    try {
      const result = await api.history.replay(historyId) as any
      requestEditor.setSent(result)
    } catch (e: any) {
      workspace.setError(e.message || 'Failed to replay history item')
    }
    setActiveHistoryId(null)
  }, [dirty, requestEditor, workspace])

  const handleCreateRequestInCollection = useCallback((collectionId: string) => {
    requestEditor.reset(collectionId)
  }, [requestEditor])

  return <div className={`app-shell workspace-app ${lightTheme ? 'light-theme' : ''}`}>
    <TopNavigation
      lightTheme={lightTheme}
      aiOpen={aiOpen}
      environments={workspace.environments}
      onRefreshEnvironments={workspace.load}
      onNavigateToEnvironments={() => setActiveNav('Environments')}
      onToggleTheme={() => setLightTheme(value => !value)}
      onToggleAI={() => setAiOpen(value => !value)}
      onLogout={logout}
    />
    <div className="workspace">
      <WorkspaceSidebar
        activeNav={activeNav}
        collections={workspace.collections}
        requests={workspace.requests}
        activeRequestId={requestEditor.active?.id}
        onActiveNavChange={setActiveNav}
        onNewRequest={() => requestEditor.reset()}
        onOpenRequest={requestEditor.openRequest}
        onOpenAI={() => setAiOpen(true)}
        onRefresh={workspace.load}
        onCreateRequestInCollection={handleCreateRequestInCollection}
      />
      {activeNav === 'Environments' ? (
        <EnvironmentPanel environments={workspace.environments} onRefresh={workspace.load} />
      ) : activeHistoryId ? (
        <ExecutionDetailView 
          historyId={activeHistoryId}
          environments={workspace.environments}
          onBack={() => setActiveHistoryId(null)}
          onOpenAsNewRequest={handleOpenAsNewRequest}
          onReplay={(snapshot, envId) => handleReplay(snapshot, envId, activeHistoryId)}
        />
      ) : (
        <RequestWorkspace
        tabs={requestEditor.tabs.map(t => ({ tabId: t.tabId, name: t.draft.name, dirty: fingerprint(t.draft) !== t.savedFingerprint }))}
        activeEditorTabId={requestEditor.activeTabId}
        onSelectTab={requestEditor.setActiveTabId}
        onCloseTab={requestEditor.closeTab}
        draft={requestEditor.draft}
        requests={workspace.requests}
        collections={workspace.collections}
        environments={workspace.environments}
        loading={workspace.loading}
        working={requestEditor.working}
        dirty={dirty}
        error={workspace.error}
        activeNav={activeNav}
        activeTab={activeTab}
        editorLoading={requestEditor.editorLoading}
        sent={requestEditor.sent}
        onDraftChange={requestEditor.setDraft}
        onActiveTabChange={setActiveTab}
        onNewRequest={() => requestEditor.reset()}
        onOpenRequest={requestEditor.openRequest}
        onSave={requestEditor.save}
        onSend={requestEditor.execute}
        onClearResponse={() => requestEditor.setSent(null)}
        onClearConsole={() => {
          if (requestEditor.sent) {
            requestEditor.setSent({ ...requestEditor.sent, console_logs: [] })
          }
        }}
        onRefresh={workspace.load}
        onSelectHistory={handleSelectHistory}
      />)}
      <AIAssistantPanel
        open={aiOpen}
        method={requestEditor.draft.method}
        url={requestEditor.draft.url}
        onClose={() => setAiOpen(false)}
        onAsk={askAI}
        conversation={aiConversation}
        loading={aiLoading}
      />
    </div>
  </div>
}
