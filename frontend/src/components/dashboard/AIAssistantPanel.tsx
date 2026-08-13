import { Bot, X, Mic, Send } from 'lucide-react'

type AIAssistantPanelProps = {
  open: boolean
  method: string
  url: string
  onClose: () => void
  onAsk: (prompt: string) => void
  conversation: { role: 'user' | 'ai', content: string }[]
  loading: boolean
}

export function AIAssistantPanel({ open, method, url, onClose, onAsk, conversation, loading }: AIAssistantPanelProps) {
  return <aside className={`ai-panel ${open ? '' : 'ai-closed'}`} style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg)' }}>
    <div className="panel-heading" style={{ padding: '16px', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
      <div>
        <span className="eyebrow" style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.02em' }}>Workspace tool</span>
        <h2 style={{ display: 'flex', alignItems: 'center', gap: '6px', margin: '4px 0 0', fontSize: '15px' }}><Bot size={16}/>AI assistant</h2>
      </div>
      <button className="icon-button" onClick={onClose} style={{ padding: '4px', background: 'transparent', border: 'none', cursor: 'pointer' }}><X size={16}/></button>
    </div>
    
    <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
      <div className="ai-context" style={{ margin: '0 16px 16px', padding: '12px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '12px' }}>
        <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.02em' }}>Current request</div>
        <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '12px', wordBreak: 'break-all' }}>
          <strong style={{ color: 'var(--syntax-get, #347043)' }}>{method}</strong> {url || <span style={{ color: 'var(--text-muted)' }}>No URL</span>}
        </div>
      </div>
      
      {conversation.length === 0 && (
        <div style={{ margin: '0 16px 16px', border: '1px solid var(--border)', borderRadius: '12px', overflow: 'hidden', background: 'var(--surface)' }}>
          <div style={{ padding: '12px 12px 8px', fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.02em' }}>Suggested actions</div>
          <div className="suggestions" style={{ display: 'flex', flexDirection: 'column' }}>
            {['Explain this request', 'Add authentication', 'Generate response tests'].map((label, idx) => (
              <button 
                key={label} 
                type="button" 
                onClick={() => onAsk(label)} 
                disabled={loading} 
                style={{ 
                  textAlign: 'left', 
                  padding: '10px 12px', 
                  background: 'transparent', 
                  border: 'none', 
                  borderTop: idx === 0 ? 'none' : '1px solid var(--border)', 
                  cursor: 'pointer', 
                  fontSize: '13px', 
                  color: 'var(--text)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}
                onMouseOver={(e) => e.currentTarget.style.background = 'var(--surface-2, #f5f5f5)'}
                onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
              >
                <span style={{ color: 'var(--brand)' }}>✧</span> {label}
              </button>
            ))}
          </div>
        </div>
      )}

      {conversation.length > 0 && (
        <div className="ai-conversation" style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '0 16px 16px' }}>
          <div className="ai-section-heading" style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.02em' }}>Conversation</div>
          {conversation.map((msg, idx) => (
            <div key={idx} style={{ 
              padding: '10px 14px', 
              borderRadius: '12px', 
              background: msg.role === 'user' ? 'var(--brand, #007bff)' : 'var(--surface)', 
              color: msg.role === 'user' ? '#fff' : 'var(--text)',
              border: msg.role === 'user' ? 'none' : '1px solid var(--border)',
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start', 
              maxWidth: '90%', 
              fontSize: '13px',
              borderBottomRightRadius: msg.role === 'user' ? '4px' : '12px',
              borderBottomLeftRadius: msg.role === 'ai' ? '4px' : '12px'
            }}>
              <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.4' }}>{msg.content}</div>
            </div>
          ))}
          {loading && <div style={{ fontSize: '13px', color: 'var(--text-muted)', display: 'flex', gap: '8px', alignItems: 'center' }}>
            <Bot size={14}/> Thinking...
          </div>}
        </div>
      )}
    </div>

    <form className="ai-conversation-input" style={{ borderTop: '1px solid var(--border)', padding: '16px', background: 'var(--bg)' }} onSubmit={event => { event.preventDefault(); const input = event.currentTarget.elements.namedItem('aiPrompt') as HTMLInputElement; if (!input.value.trim()) return; onAsk(input.value); input.value = '' }}>
      <div style={{ display: 'flex', alignItems: 'center', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '24px', padding: '4px 8px', boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
        <button type="button" disabled={loading} style={{ padding: '6px', background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '50%' }} onMouseOver={(e) => e.currentTarget.style.background = 'var(--surface-2, #f5f5f5)'} onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}>
          <Mic size={18}/>
        </button>
        <input name="aiPrompt" aria-label="Ask AI" placeholder="Ask anything..." disabled={loading} style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none', padding: '6px 8px', fontSize: '13px', color: 'var(--text)' }}/>
        <button type="submit" disabled={loading} style={{ padding: '6px', background: 'var(--text)', color: 'var(--bg)', border: 'none', borderRadius: '50%', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', width: '30px', height: '30px' }}>
          <Send size={14}/>
        </button>
      </div>
    </form>
  </aside>
}
