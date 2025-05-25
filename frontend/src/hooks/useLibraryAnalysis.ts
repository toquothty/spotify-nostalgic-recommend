import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { recommendationsApi } from '../services/api'

interface LibraryStatus {
  library_analyzed: boolean
  track_count: number
  cluster_count: number
  recommendation_count: number
  can_generate_recommendations: boolean
  needs_onboarding: boolean
  last_recommendation: string | null
  recommendations_today: number
  total_liked_songs: number
}

interface AnalysisResult {
  message: string
  status: string
  track_count?: number
  estimated_time?: string
}

export const useLibraryAnalysis = () => {
  const { sessionId } = useAuth()
  const [status, setStatus] = useState<LibraryStatus | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchStatus = async () => {
    if (!sessionId) return

    try {
      setIsLoading(true)
      setError(null)
      const statusData = await recommendationsApi.getStatus(sessionId)
      setStatus(statusData)
    } catch (err) {
      setError('Failed to fetch library status')
      console.error('Status fetch error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const analyzeLibrary = async (trackLimit: number = 1000): Promise<AnalysisResult | null> => {
    if (!sessionId) return null

    try {
      setIsAnalyzing(true)
      setError(null)
      const result = await recommendationsApi.analyzeLibrary(sessionId, trackLimit)
      
      // Refresh status after starting analysis
      setTimeout(fetchStatus, 1000)
      
      return result
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Failed to analyze library'
      setError(errorMessage)
      console.error('Analysis error:', err)
      return null
    } finally {
      setIsAnalyzing(false)
    }
  }

  // Fetch status on mount and when sessionId changes
  useEffect(() => {
    if (sessionId) {
      fetchStatus()
    }
  }, [sessionId])

  // Poll for status updates when analyzing
  useEffect(() => {
    if (!isAnalyzing || !sessionId) return

    const interval = setInterval(fetchStatus, 5000) // Poll every 5 seconds
    return () => clearInterval(interval)
  }, [isAnalyzing, sessionId])

  return {
    status,
    isLoading,
    isAnalyzing,
    error,
    analyzeLibrary,
    refreshStatus: fetchStatus,
  }
}
