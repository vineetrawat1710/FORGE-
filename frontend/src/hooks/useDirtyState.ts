import { useEffect } from 'react'
import type { RequestDraft } from '../types/api'
import { fingerprint } from '../utils/requestSerialization'

export function useDirtyState(draft: RequestDraft, savedFingerprint: string) {
  return fingerprint(draft) !== savedFingerprint
}

export function useSaveShortcut(options: { dirty: boolean; working: boolean; onSave: () => void }) {
  const { dirty, working, onSave } = options

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
        event.preventDefault()
        if (!working) onSave()
      }
    }

    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      if (!dirty) return
      event.preventDefault()
      event.returnValue = ''
    }

    window.addEventListener('keydown', onKeyDown)
    window.addEventListener('beforeunload', onBeforeUnload)
    return () => {
      window.removeEventListener('keydown', onKeyDown)
      window.removeEventListener('beforeunload', onBeforeUnload)
    }
  }, [dirty, onSave, working])
}
