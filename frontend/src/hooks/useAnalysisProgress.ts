import { useState, useEffect, useRef } from 'react'
import { progressApi } from '../services/api'

interface AnalysisProgress {
  status: string
  current_step: string
  progress_percentage: number
  tracks_processed: number
  total_tracks: number
  error_message?: string
  started_at?: string
  completed_at?: string
  updated_at?: string
}

interface UseAnalysisProgressReturn {
  progress: AnalysisProgress | null
  isLoading: boolean
  error: string | null
  startPolling: () => void
  stopPolling: () => void
}

export const useAnalysisProgress = (sessionId: string | null): UseAnalysisProgressReturn => {
  const [progress, setProgress] = useState<AnalysisProgress | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isPolling, setIsPolling] = useState(false)
  const intervalRef = useRef<number | null>(null)

  const fetchProgress = async () => {
    if (!sessionId) return

    try {
      setError(null)
      const progressData = await progressApi.getAnalysisProgress(sessionId)

      setProgress(progressData)

      // Stop polling if analysis is completed or failed
      if (progressData.status === 'completed' || progressData.status === 'failed') {
        stopPolling()
      }
    } catch (err: any) {
      console.error('Failed to fetch progress:', err)
      setError(err.response?.data?.detail || 'Failed to fetch progress')
      
      // Stop polling on error
      stopPolling()
    }
  }

  const startPolling = () => {
    if (isPolling || !sessionId) return

    setIsPolling(true)
    setIsLoading(true)

    // Fetch immediately
    fetchProgress()

    // Then poll every 2 seconds
    intervalRef.current = window.setInterval(fetchProgress, 2000)
  }

  const stopPolling = () => {
    setIsPolling(false)
    setIsLoading(false)

    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopPolling()
    }
  }, [])

  // Auto-start polling when sessionId changes and we have one
  useEffect(() => {
    if (sessionId && !isPolling) {
      // Check if we should start polling based on current progress
      fetchProgress().then(() => {
        if (progress && ['starting', 'fetching_tracks', 'getting_features', 'clustering'].includes(progress.status)) {
          startPolling()
        }
      })
    }
  }, [sessionId])

  return {
    progress,
    isLoading,
    error,
    startPolling,
    stopPolling
  }
}
