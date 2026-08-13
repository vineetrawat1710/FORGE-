import { useState, useCallback, useMemo, useEffect } from 'react'
import { Plus, Trash2, Edit2, Search, Check, MoreVertical, Filter, Eye, EyeOff, Lock } from 'lucide-react'
import type { EnvironmentSummary, EnvironmentDetail, EnvironmentVariable } from '../../types/api'
import { api } from '../../api'

type EnvironmentPanelProps = {
  environments: EnvironmentSummary[]
  onRefresh: () => void
}

const ENV_COLORS: Record<string, string> = {
  local: '#22c55e',
  development: '#3b82f6',
  staging: '#f59e0b',
  production: '#ef4444'
}

function getEnvColor(name: string) {
  const n = name.toLowerCase()
  if (n.includes('local')) return ENV_COLORS.local
  if (n.includes('dev')) return ENV_COLORS.development
  if (n.includes('stage') || n.includes('staging')) return ENV_COLORS.staging
  if (n.includes('prod')) return ENV_COLORS.production
  return '#94a3b8'
}

export function EnvironmentPanel({ environments, onRefresh }: EnvironmentPanelProps) {
  const [selectedId, setSelectedId] = useState<string | null>(environments[0]?.id || null)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [createName, setCreateName] = useState('')
  const [isRenaming, setIsRenaming] = useState(false)
  const [renameValue, setRenameValue] = useState('')
  const [activeTab, setActiveTab] = useState<'overview' | 'variables'>('overview')

  const selectedEnv = environments.find(e => e.id === selectedId)
  
  const [selectedDetail, setSelectedDetail] = useState<EnvironmentDetail | null>(null)
  const [variablesDraft, setVariablesDraft] = useState<Array<{ key: string } & EnvironmentVariable>>([])
  const [revealedSecrets, setRevealedSecrets] = useState<Set<number>>(new Set())
  const [isSavingVariables, setIsSavingVariables] = useState(false)
  const [varsError, setVarsError] = useState('')

  useEffect(() => {
    if (!selectedId) {
      setSelectedDetail(null)
      setVariablesDraft([])
      setRevealedSecrets(new Set())
      return
    }
    
    let active = true
    api.environments.get(selectedId).then((detail: EnvironmentDetail) => {
      if (active) {
        setSelectedDetail(detail)
        const draft = Object.entries(detail.variables || {}).map(([key, val]) => ({
          key,
          value: val.value || '',
          enabled: val.enabled ?? true,
          secret: val.secret || false,
          description: val.description || ''
        }))
        setVariablesDraft(draft)
        setRevealedSecrets(new Set())
      }
    }).catch(err => {
      if (active) setVarsError(err.message || 'Failed to load environment variables')
    })

    return () => { active = false }
  }, [selectedId, environments]) // Also re-fetch if environments changes (like after a refresh/update)

  const hasUnsavedChanges = useMemo(() => {
    if (!selectedDetail) return false
    
    const draftKeys = variablesDraft.map(v => v.key.trim()).filter(Boolean)
    const detailKeys = Object.keys(selectedDetail.variables || {})
    
    if (draftKeys.length !== detailKeys.length) return true
    
    for (const v of variablesDraft) {
      const key = v.key.trim()
      if (!key) continue
      const existing = selectedDetail.variables[key]
      if (!existing) return true
      if (v.value !== existing.value || v.enabled !== existing.enabled || v.secret !== existing.secret || v.description !== existing.description) {
        return true
      }
    }
    return false
  }, [variablesDraft, selectedDetail])

  const handleSaveVariables = async () => {
    if (!selectedId) return
    setIsSavingVariables(true)
    setVarsError('')
    
    const variables: Record<string, EnvironmentVariable> = {}
    for (const v of variablesDraft) {
      const k = v.key.trim()
      if (k) {
        if (variables[k]) {
          setVarsError(`Duplicate variable name found: "${k}". Variable names must be unique.`)
          setIsSavingVariables(false)
          return
        }
        variables[k] = {
          value: v.value,
          enabled: v.enabled,
          secret: v.secret,
          description: v.description
        }
      }
    }
    
    try {
      await api.environments.update(selectedId, { variables })
      await onRefresh()
      // Note: onRefresh will update environments array which triggers the useEffect to reload detail and reset draft
    } catch (e: any) {
      setVarsError(e.message || 'Failed to save variables')
    } finally {
      setIsSavingVariables(false)
    }
  }

  const updateDraft = (index: number, updates: Partial<{ key: string } & EnvironmentVariable>) => {
    setVariablesDraft(prev => {
      const copy = [...prev]
      copy[index] = { ...copy[index], ...updates }
      return copy
    })
  }

  const removeDraft = (index: number) => {
    setVariablesDraft(prev => prev.filter((_, i) => i !== index))
  }

  const toggleReveal = (index: number) => {
    setRevealedSecrets(prev => {
      const copy = new Set(prev)
      if (copy.has(index)) copy.delete(index)
      else copy.add(index)
      return copy
    })
  }

  const filtered = useMemo(() => {
    if (!search) return environments
    const lower = search.toLowerCase()
    return environments.filter(e => e.name.toLowerCase().includes(lower))
  }, [environments, search])

  const handleCreate = async () => {
    if (!createName.trim()) return
    setLoading(true)
    setError('')
    try {
      const created = await api.environments.create({ name: createName.trim() }) as EnvironmentSummary
      await onRefresh()
      setSelectedId(created.id)
      setIsCreating(false)
      setCreateName('')
    } catch (e: any) {
      setError(e.message || 'Failed to create environment')
    } finally {
      setLoading(false)
    }
  }

  const handleRename = async () => {
    if (!selectedId || !renameValue.trim() || !selectedEnv) return
    setLoading(true)
    setError('')
    try {
      await api.environments.update(selectedId, { name: renameValue.trim() })
      await onRefresh()
      setIsRenaming(false)
    } catch (e: any) {
      setError(e.message || 'Failed to rename environment')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!selectedId || !selectedEnv) return
    if (!confirm(`Are you sure you want to delete the environment "${selectedEnv.name}"? This cannot be undone.`)) return
    
    setLoading(true)
    setError('')
    try {
      if (selectedEnv.is_active) {
        await api.environments.deactivate()
      }
      await api.environments.remove(selectedId)
      await onRefresh()
      setSelectedId(null)
    } catch (e: any) {
      setError(e.message || 'Failed to delete environment')
    } finally {
      setLoading(false)
    }
  }

  const handleActivate = async (id: string) => {
    setLoading(true)
    setError('')
    try {
      await api.environments.activate(id)
      await onRefresh()
    } catch (e: any) {
      setError(e.message || 'Failed to activate environment')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Never'
    const d = new Date(dateString)
    return d.toLocaleString()
  }

  return (
    <div style={{ flex: 1, padding: '32px 48px', overflowY: 'auto', background: 'var(--surface, #f7f9f7)', color: '#26332a' }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
        
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
          <div>
            <h1 style={{ fontSize: '22px', fontWeight: 700, margin: '0 0 8px 0' }}>Environments</h1>
            <p style={{ margin: 0, color: '#526157', fontSize: '13px' }}>Manage your environments and their variables</p>
          </div>
          <button 
            className="primary-button" 
            onClick={() => { setIsCreating(true); setSelectedId(null); setCreateName(''); }}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 14px', background: '#347043', color: '#fff', border: 0, borderRadius: '6px', fontSize: '13px', fontWeight: 600, cursor: 'pointer' }}
          >
            <Plus size={16} /> New environment
          </button>
        </div>

        {/* Card or Empty State */}
        {environments.length === 0 && !isCreating ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '500px', border: '1px dashed #dce4dd', borderRadius: '8px', background: 'transparent', textAlign: 'center', padding: '48px', marginTop: '48px' }}>
            <h2 style={{ fontSize: '18px', fontWeight: 600, color: '#26332a', margin: '0 0 12px 0' }}>No environments yet</h2>
            <p style={{ fontSize: '13px', color: '#526157', maxWidth: '340px', lineHeight: '1.5', margin: '0 0 24px 0' }}>
              Create an environment to manage API URLs, credentials, tokens, and other variables used across your requests.
            </p>
            <button 
              className="primary-button" 
              onClick={() => setIsCreating(true)}
              style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px', background: '#347043', color: '#fff', border: 0, borderRadius: '6px', fontSize: '13px', fontWeight: 600, cursor: 'pointer' }}
            >
              <Plus size={16} /> New environment
            </button>
            <div style={{ fontSize: '12px', color: '#7b897f', marginTop: '32px' }}>
              You can create environments for Local, Development, Staging, or Production.
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', border: '1px solid #dce4dd', borderRadius: '8px', background: '#fff', height: '600px', overflow: 'hidden' }}>
          
          {/* Left Pane - List */}
          <div style={{ width: '300px', minWidth: '300px', borderRight: '1px solid #dce4dd', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: '16px', display: 'flex', gap: '8px', borderBottom: '1px solid #dce4dd' }}>
              <div style={{ position: 'relative', flex: 1 }}>
                <Search size={14} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#7b897f' }} />
                <input 
                  type="text" 
                  placeholder="Search environments..." 
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px 8px 32px', border: '1px solid #dce4dd', borderRadius: '4px', fontSize: '12px' }}
                />
              </div>
              <button style={{ width: '32px', height: '32px', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid #dce4dd', borderRadius: '4px', background: '#fff', cursor: 'pointer', color: '#526157' }}>
                <Filter size={14} />
              </button>
            </div>

            <div style={{ flex: 1, overflowY: 'auto' }}>
              {isCreating && (
                <div style={{ padding: '16px', borderBottom: '1px solid #dce4dd' }}>
                  <input
                    autoFocus
                    type="text"
                    value={createName}
                    onChange={e => setCreateName(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === 'Enter') handleCreate()
                      if (e.key === 'Escape') setIsCreating(false)
                    }}
                    placeholder="Environment name"
                    style={{ width: '100%', border: '1px solid #dce4dd', borderRadius: '4px', padding: '6px 10px', fontSize: '13px', marginBottom: '8px' }}
                  />
                  <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                    <button style={{ padding: '4px 10px', fontSize: '12px', background: 'transparent', border: '1px solid #dce4dd', borderRadius: '4px', cursor: 'pointer' }} onClick={() => setIsCreating(false)}>Cancel</button>
                    <button style={{ padding: '4px 10px', fontSize: '12px', background: '#347043', color: '#fff', border: 0, borderRadius: '4px', cursor: 'pointer' }} onClick={handleCreate} disabled={loading || !createName.trim()}>Save</button>
                  </div>
                </div>
              )}

              {filtered.map(env => {
                const color = getEnvColor(env.name)
                return (
                  <div 
                    key={env.id} 
                    onClick={() => { setSelectedId(env.id); setIsCreating(false); setIsRenaming(false); }}
                    style={{ 
                      padding: '16px', 
                      cursor: 'pointer',
                      background: selectedId === env.id ? '#f7f9f7' : '#fff',
                      borderBottom: '1px solid #dce4dd',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px',
                      position: 'relative',
                    }}
                  >
                    {selectedId === env.id && <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: '3px', background: '#347043' }} />}
                    
                    <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: color }} />
                    
                    <div style={{ flex: 1, overflow: 'hidden' }}>
                      <div style={{ fontSize: '14px', fontWeight: 700, color: '#26332a', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', marginBottom: '4px' }}>
                        {env.name}
                      </div>
                      <div style={{ fontSize: '12px', color: '#526157' }}>
                        {/* We don't have count directly on summary, this requires counting keys from variables if added to summary backend, else we just say "variables" */}
                        Variables
                      </div>
                    </div>

                    {env.is_active && (
                      <div style={{ background: '#e2f0e6', color: '#255e34', padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600 }}>
                        Active
                      </div>
                    )}

                    <button style={{ background: 'transparent', border: 0, color: '#7b897f', cursor: 'pointer' }}>
                      <MoreVertical size={16} />
                    </button>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Right Pane - Details */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            {error && (
              <div style={{ margin: '16px', padding: '12px', background: '#f8e3e3', color: '#b33a3a', fontSize: '12px', borderRadius: '4px', border: '1px solid rgba(179,58,58,0.2)' }}>
                <strong>Error:</strong> {error}
              </div>
            )}
            
            {selectedEnv ? (
              <div style={{ padding: '32px', flex: 1, overflowY: 'auto' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '16px' }}>
                  
                  {isRenaming ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input
                        autoFocus
                        type="text"
                        value={renameValue}
                        onChange={e => setRenameValue(e.target.value)}
                        onKeyDown={e => {
                          if (e.key === 'Enter') handleRename()
                          if (e.key === 'Escape') setIsRenaming(false)
                        }}
                        style={{ fontSize: '20px', fontWeight: 700, padding: '4px 8px', border: '1px solid #dce4dd', borderRadius: '4px', width: '250px' }}
                      />
                      <button style={{ padding: '6px 12px', background: '#347043', color: '#fff', border: 0, borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }} onClick={handleRename} disabled={loading || !renameValue.trim()}>Save</button>
                      <button style={{ padding: '6px 12px', background: '#fff', border: '1px solid #dce4dd', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }} onClick={() => setIsRenaming(false)}>Cancel</button>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: getEnvColor(selectedEnv.name) }} />
                      <h2 style={{ fontSize: '20px', fontWeight: 700, margin: 0, color: '#26332a' }}>{selectedEnv.name}</h2>
                    </div>
                  )}
                  
                  {!isRenaming && (
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button 
                        style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', background: '#fff', border: '1px solid #dce4dd', borderRadius: '4px', padding: '6px 12px', cursor: 'pointer', fontWeight: 500, color: '#26332a' }}
                        onClick={() => { setRenameValue(selectedEnv.name); setIsRenaming(true); }}
                      >
                        <Edit2 size={14} /> Rename
                      </button>
                      <button 
                        style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', background: '#fff', border: '1px solid #f8e3e3', color: '#dc2626', borderRadius: '4px', padding: '6px 12px', cursor: 'pointer', fontWeight: 500 }}
                        onClick={handleDelete}
                        disabled={loading}
                      >
                        <Trash2 size={14} /> Delete
                      </button>
                    </div>
                  )}
                </div>

                <div style={{ color: '#526157', fontSize: '12px', marginBottom: '32px' }}>
                  {selectedDetail ? Object.keys(selectedDetail.variables || {}).length : 0} variables • Updated {formatDate(selectedEnv.updated_at)}
                </div>

                <div style={{ display: 'flex', gap: '24px', borderBottom: '1px solid #dce4dd', marginBottom: '24px' }}>
                  <button 
                    onClick={() => setActiveTab('overview')}
                    style={{ background: 'transparent', border: 0, padding: '0 0 12px 0', fontSize: '13px', fontWeight: 600, color: activeTab === 'overview' ? '#26332a' : '#526157', borderBottom: activeTab === 'overview' ? '2px solid #347043' : '2px solid transparent', cursor: 'pointer', marginBottom: '-1px' }}
                  >
                    Overview
                  </button>
                  <button 
                    onClick={() => setActiveTab('variables')}
                    style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'transparent', border: 0, padding: '0 0 12px 0', fontSize: '13px', fontWeight: activeTab === 'variables' ? 600 : 500, color: activeTab === 'variables' ? '#26332a' : '#526157', borderBottom: activeTab === 'variables' ? '2px solid #347043' : '2px solid transparent', cursor: 'pointer', marginBottom: '-1px' }}
                  >
                    Variables <span style={{ background: '#eef2ef', color: '#526157', padding: '2px 6px', borderRadius: '12px', fontSize: '11px', fontWeight: 500 }}>{selectedDetail ? Object.keys(selectedDetail.variables || {}).length : 0}</span>
                  </button>
                </div>

                {activeTab === 'overview' ? (
                  <div>
                    <div style={{ marginBottom: '24px' }}>
                      <div style={{ fontSize: '13px', color: '#526157', marginBottom: '4px' }}>Description</div>
                      <div style={{ fontSize: '13px', color: '#7b897f', fontStyle: 'italic' }}>
                        {selectedEnv.description || 'No description'}
                      </div>
                    </div>
                    
                    <div>
                      <div style={{ fontSize: '13px', color: '#526157', marginBottom: '4px' }}>Last updated</div>
                      <div style={{ fontSize: '13px', color: '#7b897f' }}>
                        {formatDate(selectedEnv.updated_at)}
                      </div>
                    </div>
                    
                    {!selectedEnv.is_active && (
                      <div style={{ marginTop: '32px' }}>
                        <button 
                          className="primary-button" 
                          onClick={() => handleActivate(selectedEnv.id)} 
                          disabled={loading}
                          style={{ padding: '8px 16px', background: '#347043', color: '#fff', border: 0, borderRadius: '4px', cursor: 'pointer', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}
                        >
                          <Check size={14} /> Set as active environment
                        </button>
                      </div>
                    )}
                  </div>
                ) : (
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                      <div>
                        <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#26332a', margin: '0 0 4px 0' }}>Variables</h3>
                        <p style={{ margin: 0, color: '#526157', fontSize: '12px' }}>Manage values used by requests in this environment.</p>
                      </div>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        {hasUnsavedChanges && (
                          <button 
                            className="primary-button" 
                            onClick={handleSaveVariables} 
                            disabled={isSavingVariables}
                            style={{ padding: '6px 12px', background: '#347043', color: '#fff', border: 0, borderRadius: '4px', cursor: 'pointer', fontSize: '12px', fontWeight: 600 }}
                          >
                            {isSavingVariables ? 'Saving...' : 'Save variables'}
                          </button>
                        )}
                      </div>
                    </div>

                    {varsError && (
                      <div style={{ margin: '0 0 16px 0', padding: '12px', background: '#f8e3e3', color: '#b33a3a', fontSize: '12px', borderRadius: '4px', border: '1px solid rgba(179,58,58,0.2)' }}>
                        <strong>Error:</strong> {varsError}
                      </div>
                    )}

                    <div style={{ border: '1px solid #dce4dd', borderRadius: '6px', overflow: 'hidden' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                        <thead style={{ background: '#f7f9f7', color: '#526157', fontWeight: 600 }}>
                          <tr>
                            <th style={{ padding: '8px 12px', width: '32px', textAlign: 'center' }}></th>
                            <th style={{ padding: '8px 12px', width: '180px' }}>Variable</th>
                            <th style={{ padding: '8px 12px' }}>Value</th>
                            <th style={{ padding: '8px 12px' }}>Description</th>
                            <th style={{ padding: '8px 12px', width: '40px', textAlign: 'center' }}>Secret</th>
                            <th style={{ padding: '8px 12px', width: '40px', textAlign: 'center' }}></th>
                          </tr>
                        </thead>
                        <tbody>
                          {variablesDraft.map((v, i) => (
                            <tr key={i} style={{ borderTop: '1px solid #dce4dd', background: v.enabled ? '#fff' : '#fcfcfc', opacity: v.enabled ? 1 : 0.6 }}>
                              <td style={{ padding: '8px 12px', textAlign: 'center' }}>
                                <input 
                                  type="checkbox" 
                                  checked={v.enabled} 
                                  onChange={e => updateDraft(i, { enabled: e.target.checked })} 
                                  style={{ margin: 0, cursor: 'pointer' }}
                                />
                              </td>
                              <td style={{ padding: '8px 12px' }}>
                                <input 
                                  type="text" 
                                  placeholder="key_name"
                                  value={v.key} 
                                  onChange={e => updateDraft(i, { key: e.target.value })} 
                                  style={{ width: '100%', border: '0', background: 'transparent', fontFamily: 'var(--font-mono, ui-monospace, SFMono-Regular, monospace)', fontSize: '12px', outline: 'none', color: '#26332a' }}
                                />
                              </td>
                              <td style={{ padding: '8px 12px' }}>
                                <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                                  <input 
                                    type={v.secret && !revealedSecrets.has(i) ? "password" : "text"} 
                                    placeholder="Value"
                                    value={v.value} 
                                    onChange={e => updateDraft(i, { value: e.target.value })} 
                                    style={{ width: '100%', border: '0', background: 'transparent', fontFamily: 'var(--font-mono, ui-monospace, SFMono-Regular, monospace)', fontSize: '12px', outline: 'none', color: '#26332a', paddingRight: v.secret ? '24px' : '0' }}
                                  />
                                  {v.secret && (
                                    <button 
                                      onClick={() => toggleReveal(i)} 
                                      style={{ position: 'absolute', right: 0, background: 'transparent', border: 0, color: '#7b897f', cursor: 'pointer', padding: 0 }}
                                    >
                                      {revealedSecrets.has(i) ? <EyeOff size={14} /> : <Eye size={14} />}
                                    </button>
                                  )}
                                </div>
                              </td>
                              <td style={{ padding: '8px 12px' }}>
                                <input 
                                  type="text" 
                                  placeholder="Description..."
                                  value={v.description || ''} 
                                  onChange={e => updateDraft(i, { description: e.target.value })} 
                                  style={{ width: '100%', border: '0', background: 'transparent', fontSize: '12px', outline: 'none', color: '#526157' }}
                                />
                              </td>
                              <td style={{ padding: '8px 12px', textAlign: 'center' }}>
                                <button 
                                  onClick={() => updateDraft(i, { secret: !v.secret })} 
                                  style={{ background: 'transparent', border: 0, color: v.secret ? '#347043' : '#cdd9cf', cursor: 'pointer' }}
                                  title="Toggle secret"
                                >
                                  <Lock size={14} />
                                </button>
                              </td>
                              <td style={{ padding: '8px 12px', textAlign: 'center' }}>
                                <button 
                                  onClick={() => removeDraft(i)} 
                                  style={{ background: 'transparent', border: 0, color: '#b33a3a', cursor: 'pointer' }}
                                  title="Delete variable"
                                >
                                  <Trash2 size={14} />
                                </button>
                              </td>
                            </tr>
                          ))}
                          {variablesDraft.length === 0 && (
                            <tr>
                              <td colSpan={6} style={{ padding: '48px', textAlign: 'center', color: '#7b897f' }}>
                                No variables yet.
                              </td>
                            </tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                    
                    <button 
                      onClick={() => setVariablesDraft(prev => [...prev, { key: '', value: '', enabled: true, secret: false, description: '' }])}
                      style={{ marginTop: '12px', padding: '8px 12px', fontSize: '12px', fontWeight: 600, color: '#347043', background: 'transparent', border: '1px dashed #cdd9cf', borderRadius: '4px', cursor: 'pointer', width: '100%' }}
                    >
                      + Add variable
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#526157', fontSize: '13px', padding: '48px', textAlign: 'center' }}>
                <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: '#f7f9f7', border: '1px solid #dce4dd', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '16px', color: '#7b897f' }}>
                  <Check size={20} />
                </div>
                <h3 style={{ fontSize: '14px', fontWeight: 600, color: '#26332a', margin: '0 0 8px 0' }}>Select an environment</h3>
                <p style={{ margin: 0, color: '#7b897f', maxWidth: '280px', lineHeight: '1.5' }}>Choose an environment from the list to view its details and variables.</p>
              </div>
            )}
          </div>
        </div>
        )}
      </div>
    </div>
  )
}
