import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import type { CollectionSummary, EnvironmentSummary, RequestItem } from '../types/api'

export function useWorkspaceData() {
  const [collections, setCollections] = useState<CollectionSummary[]>([])
  const [requests, setRequests] = useState<RequestItem[]>([])
  const [environments, setEnvironments] = useState<EnvironmentSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [nextCollections, nextRequests, nextEnvironments] = await Promise.all([
        api.collections.list(),
        api.requests.list(),
        api.environments.list(),
      ])
      setCollections(nextCollections as CollectionSummary[])
      setRequests(nextRequests as RequestItem[])
      setEnvironments(nextEnvironments as EnvironmentSummary[])
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Unable to load workspace data.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  return { collections, requests, environments, loading, error, setError, load }
}
