import { useState, useRef, useEffect, useCallback } from 'react'
import { Check, ChevronDown, Plus, Settings, Layers } from 'lucide-react'
import { api } from '../../api'
import type { EnvironmentSummary } from '../../types/api'

type EnvironmentSelectorProps = {
  environments: EnvironmentSummary[]
  onRefresh: () => void
  onNavigateToEnvironments: () => void
}

export function EnvironmentSelector({ environments, onRefresh, onNavigateToEnvironments }: EnvironmentSelectorProps) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const menuRef = useRef<HTMLDivElement>(null)

  const activeEnvironment = environments.find(e => e.is_active)

  const handleClickOutside = useCallback((e: MouseEvent) => {
    if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
      setOpen(false)
    }
  }, [])

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape' && open) setOpen(false)
  }, [open])

  useEffect(() => {
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [handleClickOutside, handleKeyDown])

  const handleActivate = async (id: string | null) => {
    setLoading(true)
    setError('')
    try {
      if (id) {
        await api.environments.activate(id)
      } else {
        await api.environments.deactivate()
      }
      onRefresh()
      setOpen(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Activation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="env-selector-wrapper" style={{ position: 'relative', display: 'flex', alignItems: 'center', marginLeft: '16px' }} ref={menuRef}>
      <button 
        className="quiet-button" 
        style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '8px', 
          padding: '6px 12px', 
          fontSize: '13px', 
          fontWeight: 500, 
          color: 'var(--text)',
          background: open ? 'var(--surface-raised, #eaeaea)' : 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: '24px',
          cursor: 'pointer',
          transition: 'background 0.2s',
          boxShadow: '0 1px 2px rgba(0,0,0,0.04)'
        }}
        onClick={() => setOpen(!open)}
        onMouseOver={(e) => e.currentTarget.style.background = 'var(--surface-raised, #eaeaea)'}
        onMouseOut={(e) => { if (!open) e.currentTarget.style.background = 'var(--surface)' }}
        aria-haspopup="true"
        aria-expanded={open}
      >
        <Layers size={14} color="var(--muted)" />
        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {activeEnvironment ? (
            <>
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--success, #347043)' }} />
              {activeEnvironment.name}
            </>
          ) : (
            <>
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', border: '1px solid var(--muted)' }} />
              No environment
            </>
          )}
        </span>
        <ChevronDown size={14} color="var(--muted)" />
      </button>

      {open && (
        <div style={{
          position: 'absolute',
          top: '100%',
          left: 0,
          marginTop: '4px',
          width: '260px',
          background: 'var(--surface, #ffffff)',
          border: '1px solid var(--border)',
          borderRadius: '6px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
          zIndex: 100,
          display: 'flex',
          flexDirection: 'column',
          fontSize: '12px'
        }}>
          <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--border)', fontWeight: 600, color: 'var(--muted)' }}>
            Environment
          </div>
          
          <div style={{ maxHeight: '240px', overflowY: 'auto', padding: '4px 0' }}>
            {error && <div style={{ padding: '8px 12px', color: 'var(--error, #b33a3a)', fontSize: '11px', background: 'var(--error-light, #f8e3e3)', margin: '0 8px 8px', borderRadius: '4px' }}>{error}</div>}
            
            <button
              className="env-menu-item"
              disabled={loading}
              onClick={() => handleActivate(null)}
              style={{
                display: 'flex', alignItems: 'center', width: '100%', padding: '8px 12px', background: 'transparent', border: 0, textAlign: 'left', cursor: 'pointer', gap: '8px', color: 'var(--text)',
                opacity: loading ? 0.5 : 1
              }}
            >
              <div style={{ width: '14px', display: 'flex', justifyContent: 'center' }}>
                {!activeEnvironment && <Check size={14} />}
              </div>
              <Layers size={14} color="var(--muted)" />
              <span>No environment</span>
            </button>

            {environments.map(env => (
              <button
                key={env.id}
                className="env-menu-item"
                disabled={loading}
                onClick={() => handleActivate(env.id)}
                style={{
                  display: 'flex', alignItems: 'flex-start', width: '100%', padding: '8px 12px', background: 'transparent', border: 0, textAlign: 'left', cursor: 'pointer', gap: '8px', color: 'var(--text)',
                  opacity: loading ? 0.5 : 1
                }}
              >
                <div style={{ width: '14px', display: 'flex', justifyContent: 'center', marginTop: '2px' }}>
                  {env.is_active && <Check size={14} />}
                </div>
                <Layers size={14} color="var(--muted)" style={{ marginTop: '2px' }} />
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', overflow: 'hidden' }}>
                  <span style={{ fontWeight: env.is_active ? 600 : 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {env.name}
                  </span>
                </div>
              </button>
            ))}

            {environments.length === 0 && (
              <div style={{ padding: '12px', color: 'var(--muted)', textAlign: 'center', fontStyle: 'italic' }}>
                No environments exist yet.
              </div>
            )}
          </div>
          
          <div style={{ borderTop: '1px solid var(--border)', padding: '4px 0' }}>
            <button
              onClick={() => { setOpen(false); onNavigateToEnvironments(); }}
              style={{ display: 'flex', alignItems: 'center', gap: '8px', width: '100%', padding: '8px 12px', background: 'transparent', border: 0, textAlign: 'left', cursor: 'pointer', color: 'var(--text)' }}
              className="env-menu-item"
            >
              <Plus size={14} color="var(--muted)" />
              Create environment
            </button>
            <button
              onClick={() => { setOpen(false); onNavigateToEnvironments(); }}
              style={{ display: 'flex', alignItems: 'center', gap: '8px', width: '100%', padding: '8px 12px', background: 'transparent', border: 0, textAlign: 'left', cursor: 'pointer', color: 'var(--text)' }}
              className="env-menu-item"
            >
              <Settings size={14} color="var(--muted)" />
              Manage environments &rarr;
            </button>
          </div>
        </div>
      )}
      <style>{`
        .env-menu-item:hover:not(:disabled) {
          background: rgba(52, 112, 67, 0.06) !important;
        }
      `}</style>
    </div>
  )
}
