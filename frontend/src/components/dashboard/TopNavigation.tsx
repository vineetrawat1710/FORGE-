import { Bot, ChevronDown, Clock3 } from 'lucide-react'
import { useState } from 'react'
import { EnvironmentSelector } from './EnvironmentSelector'
import type { EnvironmentSummary } from '../../types/api'

type TopNavigationProps = {
  lightTheme: boolean
  aiOpen: boolean
  environments: EnvironmentSummary[]
  onRefreshEnvironments: () => void
  onNavigateToEnvironments: () => void
  onToggleTheme: () => void
  onToggleAI: () => void
  onLogout: () => void
}

export function TopNavigation({ lightTheme, aiOpen, environments, onRefreshEnvironments, onNavigateToEnvironments, onToggleTheme, onToggleAI, onLogout }: TopNavigationProps) {
  const [profileOpen, setProfileOpen] = useState(false)

  return <header className="topbar">
    <div className="brand"><span className="brand-mark">A</span><span>API Studio</span><span className="brand-ai">AI</span></div>
    <button className="workspace-switcher">Personal workspace <ChevronDown size={14}/></button>
    <div className="global-search"><span>Search requests...</span><kbd>⌘ K</kbd></div>
    <EnvironmentSelector environments={environments} onRefresh={onRefreshEnvironments} onNavigateToEnvironments={onNavigateToEnvironments} />
    <div className="top-actions">
      <button type="button" className="ai-toggle quiet-button" title={aiOpen ? 'Close AI assistant' : 'Open AI assistant'} aria-label={aiOpen ? 'Close AI assistant' : 'Open AI assistant'} aria-pressed={aiOpen} onClick={onToggleAI}><Bot size={17}/></button>
      <button className="theme-toggle" onClick={onToggleTheme}>{lightTheme ? '☾' : '☀'}</button>
      <button className="logout-button" onClick={onLogout}>Log out</button>
      <button className="quiet-button">⌘ K</button>
      <button className="icon-button"><Clock3 size={16}/></button>
      <button className="avatar">V</button>
      <button className="profile-menu" aria-label="Open profile menu" onClick={() => setProfileOpen(value => !value)}>V ▾</button>
      <div className={`profile-dropdown ${profileOpen ? 'open' : ''}`}><strong>Personal Workspace</strong><button type="button" onClick={onLogout}>Log out</button></div>
    </div>
  </header>
}
