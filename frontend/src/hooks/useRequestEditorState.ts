import { useCallback, useState } from 'react'
import { api } from '../api'
import type { ExecutionResult, RequestDraft, RequestItem } from '../types/api'
import { defaultDraft, draftFromRequest, fingerprint, savePayloadFromDraft } from '../utils/requestSerialization'

export type EditorTab = {
  tabId: string
  active: RequestItem | null
  draft: RequestDraft
  savedFingerprint: string
  sent: ExecutionResult | null
}

export function useRequestEditorState(loadWorkspace: () => Promise<void>, setGlobalError: (value: string) => void) {
  const initialDraft = defaultDraft()
  const initialTabId = crypto.randomUUID()
  const [tabs, setTabs] = useState<EditorTab[]>(() => [{
    tabId: initialTabId,
    active: null,
    draft: initialDraft,
    savedFingerprint: fingerprint(initialDraft),
    sent: null,
  }])
  const [activeTabId, setActiveTabId] = useState<string | null>(initialTabId)
  const [editorLoading, setEditorLoading] = useState(false)
  const [working, setWorking] = useState(false)

  const activeTab = tabs.find(t => t.tabId === activeTabId) || null

  const openRequest = useCallback(async (item: RequestItem) => {
    // Check if a tab for this request already exists
    const existing = tabs.find(t => t.active?.id === item.id)
    if (existing) {
      setActiveTabId(existing.tabId)
      return
    }

    setEditorLoading(true)
    setGlobalError('')
    try {
      const loaded = (await api.requests.get(item.id)) as RequestItem
      const nextDraft = draftFromRequest(loaded)
      const newTab: EditorTab = {
        tabId: crypto.randomUUID(),
        active: loaded,
        draft: nextDraft,
        savedFingerprint: fingerprint(nextDraft),
        sent: null,
      }
      setTabs(prev => [...prev, newTab])
      setActiveTabId(newTab.tabId)
    } catch (error) {
      setGlobalError(error instanceof Error ? error.message : 'Unable to load request.')
    } finally {
      setEditorLoading(false)
    }
  }, [tabs, setGlobalError])

  const reset = useCallback((collectionId?: string | null) => {
    const nextDraft = defaultDraft(collectionId)
    const newTab: EditorTab = {
      tabId: crypto.randomUUID(),
      active: null,
      draft: nextDraft,
      savedFingerprint: fingerprint(nextDraft),
      sent: null,
    }
    setTabs(prev => [...prev, newTab])
    setActiveTabId(newTab.tabId)
  }, [])

  const closeTab = useCallback((tabId: string) => {
    setTabs(prev => {
      const nextTabs = prev.filter(t => t.tabId !== tabId)
      if (activeTabId === tabId) {
        if (nextTabs.length > 0) {
          // Switch to the previous tab or the first available
          const closedIndex = prev.findIndex(t => t.tabId === tabId)
          const fallback = nextTabs[closedIndex - 1] || nextTabs[0]
          setActiveTabId(fallback.tabId)
        } else {
          setActiveTabId(null)
        }
      }
      return nextTabs
    })
  }, [activeTabId])

  const setDraft = useCallback((nextDraft: RequestDraft) => {
    if (!activeTabId) return
    setTabs(prev => prev.map(t => t.tabId === activeTabId ? { ...t, draft: nextDraft } : t))
  }, [activeTabId])

  const setSent = useCallback((result: ExecutionResult | null) => {
    if (!activeTabId) return
    setTabs(prev => prev.map(t => t.tabId === activeTabId ? { ...t, sent: result } : t))
  }, [activeTabId])

  const save = useCallback(async () => {
    if (!activeTab) return
    setWorking(true)
    setGlobalError('')
    try {
      const payload = savePayloadFromDraft(activeTab.draft, activeTab.active)
      const saved = activeTab.active 
        ? await api.requests.update(activeTab.active.id, payload) 
        : await api.requests.create(payload)
        
      const reloaded = (await api.requests.get((saved as RequestItem).id)) as RequestItem
      const nextDraft = draftFromRequest(reloaded)
      
      setTabs(prev => prev.map(t => t.tabId === activeTabId ? {
        ...t,
        active: reloaded,
        draft: nextDraft,
        savedFingerprint: fingerprint(nextDraft),
      } : t))
      
      await loadWorkspace()
    } catch (error) {
      setGlobalError(error instanceof Error ? error.message : 'Unable to save request.')
    } finally {
      setWorking(false)
    }
  }, [activeTab, activeTabId, loadWorkspace, setGlobalError])

  const execute = useCallback(async () => {
    if (!activeTab || !activeTab.active) {
      setGlobalError('Save this request to a collection before sending it.')
      return
    }
    setWorking(true)
    setGlobalError('')
    try {
      const result = (await api.requests.execute(activeTab.active.id)) as ExecutionResult
      setTabs(prev => prev.map(t => t.tabId === activeTabId ? { ...t, sent: result } : t))
      
      try {
        await api.ai.explainResponse({
          status_code: result.status_code || 0,
          headers: result.headers || {},
          body: result.body || '',
          response: result,
        })
      } catch {
        // AI analysis is optional for this workspace path.
      }
    } catch (error) {
      setGlobalError(error instanceof Error ? error.message : 'Request execution failed.')
    } finally {
      setWorking(false)
    }
  }, [activeTab, activeTabId, setGlobalError])

  return {
    tabs,
    activeTabId,
    setActiveTabId,
    closeTab,
    
    active: activeTab?.active || null,
    draft: activeTab?.draft || defaultDraft(),
    savedFingerprint: activeTab?.savedFingerprint || '',
    sent: activeTab?.sent || null,
    
    setDraft,
    setSent,
    
    editorLoading,
    working,
    openRequest,
    reset,
    save,
    execute,
  }
}
