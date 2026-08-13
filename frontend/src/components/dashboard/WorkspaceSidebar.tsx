import { Bot, Folder, History, Layers, Plus, Settings, ChevronDown, FileText, MoreVertical } from 'lucide-react'
import { useState, useEffect } from 'react'
import type { CollectionSummary, RequestItem } from '../../types/api'
import { api } from '../../api'

type WorkspaceSidebarProps = {
  activeNav: string
  collections: CollectionSummary[]
  requests: RequestItem[]
  activeRequestId?: string
  onActiveNavChange: (value: string) => void
  onNewRequest: () => void
  onOpenRequest: (request: RequestItem) => void
  onOpenAI: () => void
  onRefresh?: () => void
  onCreateRequestInCollection?: (collectionId: string) => void
}

const nav = [
  { label: 'Collections', icon: Folder },
  { label: 'Environments', icon: Layers },
  { label: 'History', icon: History },
  { label: 'AI Assistant', icon: Bot },
]

export function WorkspaceSidebar({
  activeNav,
  collections,
  requests,
  activeRequestId,
  onActiveNavChange,
  onNewRequest,
  onOpenRequest,
  onOpenAI,
  onRefresh,
  onCreateRequestInCollection,
}: WorkspaceSidebarProps) {
  const [collectionsOpen, setCollectionsOpen] = useState(true)
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set())

  const [modalState, setModalState] = useState<'create' | 'edit' | 'delete' | null>(null)
  const [activeCollectionId, setActiveCollectionId] = useState<string | null>(null)
  const [modalInputValue, setModalInputValue] = useState('')
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  const activeCollectionName = collections.find(c => c.id === activeCollectionId)?.name || ''

  useEffect(() => {
    const handleClick = () => setMenuOpenId(null)
    const handleEscape = (e: KeyboardEvent) => { if (e.key === 'Escape') setMenuOpenId(null) }
    window.addEventListener('click', handleClick)
    window.addEventListener('keydown', handleEscape)
    return () => {
      window.removeEventListener('click', handleClick)
      window.removeEventListener('keydown', handleEscape)
    }
  }, [])

  const toggleGroup = (id: string) => {
    setCollapsedGroups(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleCreate = async () => {
    const name = modalInputValue.trim()
    if (!name) return
    setIsSubmitting(true)
    setErrorMessage('')
    try {
      await api.collections.create({ name })
      setModalState(null)
      onRefresh?.()
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to create collection.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleEdit = async () => {
    const name = modalInputValue.trim()
    if (!name || !activeCollectionId) return
    setIsSubmitting(true)
    setErrorMessage('')
    try {
      await api.collections.update(activeCollectionId, { name })
      setModalState(null)
      onRefresh?.()
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to rename collection.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async () => {
    if (!activeCollectionId) return
    setIsSubmitting(true)
    setErrorMessage('')
    try {
      await api.collections.remove(activeCollectionId)
      
      setModalState(null)
      onRefresh?.()
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to delete collection.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const openCreateModal = () => {
    setModalInputValue('')
    setErrorMessage('')
    setModalState('create')
  }

  const openEditModal = (id: string, currentName: string) => {
    setActiveCollectionId(id)
    setModalInputValue(currentName)
    setErrorMessage('')
    setModalState('edit')
    setMenuOpenId(null)
  }

  const openDeleteModal = (id: string) => {
    setActiveCollectionId(id)
    setErrorMessage('')
    setModalState('delete')
    setMenuOpenId(null)
  }

  const byCollection = new Map<string, RequestItem[]>()
  requests.forEach(item => {
    const key = item.collection_id || 'unfiled'
    byCollection.set(key, [...(byCollection.get(key) || []), item])
  })
  const unfiled = byCollection.get('unfiled') || []

  return <aside className="rail">
    <style>{`
      .collection-action-btn { opacity: 0; }
      .explorer-heading:hover .collection-action-btn, 
      .explorer-group-heading:hover .collection-action-btn,
      .collection-action-btn:focus-visible { opacity: 1; }
      .collection-action-btn:hover { background: var(--border); }
      .ctx-menu-item { padding: 6px 12px; cursor: pointer; font-size: 12px; text-align: left; color: var(--text); }
      .ctx-menu-item:hover { background: var(--surface-2); }
      .ctx-menu-item.danger { color: #ef4444; }
      .ctx-menu-item:focus-visible { outline: 1px solid var(--accent); background: var(--surface-2); }
      .explorer-heading:after { display: none !important; }
    `}</style>

    <button className="new-request" onClick={onNewRequest}><Plus size={17}/> New request</button>
    <nav>{nav.map(({ label, icon: Icon }) => <button key={label} className={`nav-item ${activeNav === label ? 'active' : ''}`} onClick={() => { if (label === 'AI Assistant') onOpenAI(); onActiveNavChange(label) }}><Icon size={16}/>{label}</button>)}</nav>
    <section className={`collection-explorer ${collectionsOpen ? '' : 'collapsed'}`}>
      <button className={`explorer-heading ${activeNav === 'Collections' ? 'active' : ''}`} type="button" aria-expanded={collectionsOpen} onClick={() => { setCollectionsOpen(value => !value); onActiveNavChange('Collections') }} style={{ display: 'flex', alignItems: 'center', width: '100%', paddingRight: '12px' }}>
        <div style={{ flex: 1, textAlign: 'left' }}>Collections</div>
        
        <div 
          style={{ display: 'flex', alignItems: 'center', marginRight: '4px', padding: '2px', cursor: 'pointer', borderRadius: '4px' }}
          onClick={(e) => { e.stopPropagation(); openCreateModal(); }}
          className="collection-action-btn"
          title="Create collection"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); openCreateModal(); } }}
        >
          <Plus size={14} color="var(--muted)" />
        </div>

        <span style={{ display: 'flex', alignItems: 'center', transform: collectionsOpen ? 'none' : 'rotate(-90deg)', transition: 'transform 150ms ease' }}>
          <ChevronDown size={14} color="var(--muted)" />
        </span>
      </button>
      <div className="explorer-content">
        {!collections.length && !requests.length ? <div className="explorer-empty"><span>No collections yet</span><button type="button" onClick={openCreateModal}>Create one</button><button type="button">Import collection</button></div> : null}
        
        {collections.map(collection => (
          <div className={`explorer-group ${collapsedGroups.has(collection.id) ? 'collapsed' : ''}`} key={collection.id}>
            <button className="explorer-group-heading" type="button" onClick={() => toggleGroup(collection.id)} style={{ display: 'flex', alignItems: 'center', width: '100%', paddingRight: '12px', paddingLeft: '20px', position: 'relative' }}>
              <Folder size={14} style={{ marginRight: '6px', color: 'var(--muted)', flexShrink: 0 }} />
              <div style={{ flex: 1, textAlign: 'left', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{collection.name}</div>
              
              <div 
                style={{ display: 'flex', alignItems: 'center', marginLeft: '4px', padding: '2px', cursor: 'pointer', borderRadius: '4px' }}
                onClick={(e) => { e.stopPropagation(); onCreateRequestInCollection?.(collection.id) }}
                className="collection-action-btn"
                tabIndex={0}
                aria-label="Create request in collection"
                title="Create request in collection"
                onKeyDown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); onCreateRequestInCollection?.(collection.id) } }}
              >
                <Plus size={14} color="var(--muted)" />
              </div>

              <div 
                style={{ display: 'flex', alignItems: 'center', marginLeft: '4px', padding: '2px', cursor: 'pointer', borderRadius: '4px' }}
                onClick={(e) => { e.stopPropagation(); setMenuOpenId(menuOpenId === collection.id ? null : collection.id) }}
                className="collection-action-btn"
                tabIndex={0}
                aria-label="Collection options"
                onKeyDown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); setMenuOpenId(menuOpenId === collection.id ? null : collection.id) } }}
              >
                <MoreVertical size={14} color="var(--muted)" />
              </div>

              <span style={{ display: 'flex', alignItems: 'center' }}>
                <ChevronDown size={14} color="var(--muted)" />
              </span>

              {menuOpenId === collection.id && (
                <div 
                  style={{ position: 'absolute', right: '12px', top: '100%', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '4px', zIndex: 50, padding: '4px 0', boxShadow: '0 2px 8px rgba(0,0,0,0.1)', minWidth: '120px' }}
                  onClick={e => e.stopPropagation()}
                >
                  <div className="ctx-menu-item" tabIndex={0} onClick={() => openEditModal(collection.id, collection.name)} onKeyDown={e => { if (e.key === 'Enter') openEditModal(collection.id, collection.name) }}>Rename</div>
                  <div className="ctx-menu-item danger" tabIndex={0} onClick={() => openDeleteModal(collection.id)} onKeyDown={e => { if (e.key === 'Enter') openDeleteModal(collection.id) }}>Delete</div>
                </div>
              )}
            </button>
            <div className="explorer-items">
              {(byCollection.get(collection.id) || []).map(item => (
                <button type="button" key={item.id} className={`explorer-request ${activeRequestId === item.id ? 'active' : ''}`} onClick={() => onOpenRequest(item)} style={{ paddingLeft: '32px' }}>
                  <FileText size={12} style={{ marginRight: '6px', color: 'var(--muted)', flexShrink: 0 }} />
                  <b className={`method-${item.method.toLowerCase()}`}>{item.method}</b>
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.name}</span>
                </button>
              ))}
            </div>
          </div>
        ))}

        {unfiled.length ? (
          <div className={`explorer-group ${collapsedGroups.has('unfiled') ? 'collapsed' : ''}`}>
            <button className="explorer-group-heading" type="button" onClick={() => toggleGroup('unfiled')} style={{ display: 'flex', alignItems: 'center', width: '100%', paddingRight: '12px', paddingLeft: '20px' }}>
              <Folder size={14} style={{ marginRight: '6px', color: 'var(--muted)', flexShrink: 0 }} />
              <div style={{ flex: 1, textAlign: 'left' }}>Drafts</div>
              <span style={{ display: 'flex', alignItems: 'center' }}>
                <ChevronDown size={14} color="var(--muted)" />
              </span>
            </button>
            <div className="explorer-items">
              {unfiled.map(item => (
                <button type="button" key={item.id} className={`explorer-request ${activeRequestId === item.id ? 'active' : ''}`} onClick={() => onOpenRequest(item)} style={{ paddingLeft: '32px' }}>
                  <FileText size={12} style={{ marginRight: '6px', color: 'var(--muted)', flexShrink: 0 }} />
                  <b className={`method-${item.method.toLowerCase()}`}>{item.method}</b>
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.name}</span>
                </button>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </section>
    <div className="rail-bottom"><button className="nav-item"><Settings size={16}/>Settings</button></div>

    {modalState === 'create' || modalState === 'edit' ? (
      <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }} onClick={() => setModalState(null)}>
        <div style={{ background: 'var(--surface)', padding: '20px', borderRadius: '8px', width: '320px', border: '1px solid var(--border)', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} onClick={e => e.stopPropagation()}>
          <h3 style={{ margin: '0 0 16px 0', fontSize: '14px', color: 'var(--text)', fontWeight: 600 }}>
            {modalState === 'create' ? 'New collection' : 'Rename collection'}
          </h3>
          {errorMessage && <div style={{ color: '#ef4444', fontSize: '12px', marginBottom: '8px' }}>{errorMessage}</div>}
          <div style={{ marginBottom: '4px', fontSize: '12px', color: 'var(--muted)' }}>
            {modalState === 'create' ? 'Collection name' : 'Current collection name'}
          </div>
          <input
            autoFocus
            type="text"
            value={modalInputValue}
            onChange={e => setModalInputValue(e.target.value)}
            disabled={isSubmitting}
            onKeyDown={e => {
              if (e.key === 'Enter' && !isSubmitting) {
                modalState === 'create' ? handleCreate() : handleEdit();
              } else if (e.key === 'Escape') {
                setModalState(null);
              }
            }}
            style={{ width: '100%', padding: '8px', border: '1px solid var(--border)', borderRadius: '4px', marginBottom: '20px', boxSizing: 'border-box', background: 'var(--bg)', color: 'var(--text)' }}
          />
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
            <button onClick={() => setModalState(null)} disabled={isSubmitting} style={{ padding: '6px 12px', background: 'transparent', border: '1px solid var(--border)', borderRadius: '4px', cursor: 'pointer', color: 'var(--text)' }}>Cancel</button>
            <button onClick={modalState === 'create' ? handleCreate : handleEdit} disabled={isSubmitting || !modalInputValue.trim()} style={{ padding: '6px 12px', background: 'var(--accent)', color: '#fff', border: 'none', borderRadius: '4px', cursor: modalInputValue.trim() && !isSubmitting ? 'pointer' : 'not-allowed', opacity: modalInputValue.trim() && !isSubmitting ? 1 : 0.7 }}>
              {modalState === 'create' ? 'Create collection' : 'Save'}
            </button>
          </div>
        </div>
      </div>
    ) : null}

    {modalState === 'delete' ? (
      <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }} onClick={() => setModalState(null)}>
        <div style={{ background: 'var(--surface)', padding: '20px', borderRadius: '8px', width: '360px', border: '1px solid var(--border)', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }} onClick={e => e.stopPropagation()}>
          <h3 style={{ margin: '0 0 16px 0', fontSize: '14px', color: 'var(--text)', fontWeight: 600 }}>Delete collection "{activeCollectionName}"?</h3>
          <p style={{ margin: '0 0 8px 0', fontSize: '13px', color: 'var(--text)' }}>The requests inside this collection will become ungrouped drafts.</p>
          <p style={{ margin: '0 0 20px 0', fontSize: '13px', color: 'var(--muted)' }}>This action cannot be undone.</p>
          
          {errorMessage && <div style={{ color: '#ef4444', fontSize: '12px', marginBottom: '16px' }}>{errorMessage}</div>}
          
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
            <button onClick={() => setModalState(null)} disabled={isSubmitting} style={{ padding: '6px 12px', background: 'transparent', border: '1px solid var(--border)', borderRadius: '4px', cursor: 'pointer', color: 'var(--text)' }}>Cancel</button>
            <button onClick={handleDelete} disabled={isSubmitting} style={{ padding: '6px 12px', background: '#ef4444', color: '#fff', border: 'none', borderRadius: '4px', cursor: isSubmitting ? 'not-allowed' : 'pointer', opacity: isSubmitting ? 0.7 : 1 }}>Delete collection</button>
          </div>
        </div>
      </div>
    ) : null}
  </aside>
}
