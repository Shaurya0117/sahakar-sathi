/**
 * useWorkerProfile — custom hook to fetch and manage worker profile state.
 *
 * Returns:
 *   profile     — the WorkerResponse object or null
 *   loading     — true while fetching
 *   error       — error message or null
 *   hasProfile  — true if a profile exists (vs 404 = no profile yet)
 *   refresh()   — re-fetch profile from API
 */
import { useCallback, useEffect, useState } from 'react'
import { getMyWorkerProfile } from '../services/workerService'

export function useWorkerProfile() {
  const [profile, setProfile]   = useState(null)
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)
  const [hasProfile, setHasProfile] = useState(false)

  const fetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getMyWorkerProfile()
      setProfile(res.data)
      setHasProfile(true)
    } catch (err) {
      if (err.response?.status === 404) {
        // No profile yet — expected state for new workers
        setProfile(null)
        setHasProfile(false)
      } else {
        setError(err.response?.data?.detail ?? 'Failed to load profile')
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetch()
  }, [fetch])

  return { profile, loading, error, hasProfile, refresh: fetch }
}
