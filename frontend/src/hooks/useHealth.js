/**
 * useHealth — custom hook to check backend connectivity.
 * Returns { status, loading, error }
 */
import { useState, useEffect } from 'react'
import { checkHealth } from '../services/api'

export function useHealth() {
  const [status, setStatus] = useState(null)   // 'ok' | null
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false

    checkHealth()
      .then((res) => {
        if (!cancelled) {
          setStatus(res.data.status)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message || 'Backend unreachable')
          setLoading(false)
        }
      })

    return () => { cancelled = true }
  }, [])

  return { status, loading, error }
}
