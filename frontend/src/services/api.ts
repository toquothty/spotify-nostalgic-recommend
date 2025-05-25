import axios from 'axios'
import { 
  User, 
  Recommendation, 
  AnalyticsOverview, 
  TasteEvolution, 
  RecommendationStats,
  AudioFeaturesDistribution 
} from '../types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Auth API
export const authApi = {
  initiateLogin: async (): Promise<{ auth_url: string; state: string }> => {
    const response = await api.get('/api/auth/login')
    return response.data
  },

  getCurrentUser: async (sessionId: string): Promise<User> => {
    const response = await api.get(`/api/auth/me?session_id=${sessionId}`)
    return response.data
  },

  completeOnboarding: async (sessionId: string, dateOfBirth: string): Promise<{ message: string }> => {
    const params = new URLSearchParams()
    params.append('session_id', sessionId)
    params.append('date_of_birth', dateOfBirth)
    
    const response = await api.post('/api/auth/onboarding', params, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })
    return response.data
  },

  logout: async (sessionId: string): Promise<{ message: string }> => {
    const params = new URLSearchParams()
    params.append('session_id', sessionId)
    
    const response = await api.post('/api/auth/logout', params, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })
    return response.data
  },
}

// Recommendations API
export const recommendationsApi = {
  analyzeLibrary: async (sessionId: string, trackLimit: number = 1000): Promise<{
    message: string
    status: string
    track_count?: number
    estimated_time?: string
  }> => {
    const response = await api.post('/api/recommendations/analyze-library', {
      session_id: sessionId,
      track_limit: trackLimit,
    })
    return response.data
  },

  generateRecommendations: async (
    sessionId: string, 
    type: 'cluster' | 'nostalgia' = 'cluster', 
    limit: number = 20
  ): Promise<{
    recommendations: Recommendation[]
    count: number
    type: string
  }> => {
    const response = await api.get('/api/recommendations/generate', {
      params: {
        session_id: sessionId,
        recommendation_type: type,
        limit,
      },
    })
    return response.data
  },

  getRecommendationHistory: async (
    sessionId: string, 
    limit: number = 50, 
    offset: number = 0
  ): Promise<{
    recommendations: Recommendation[]
    count: number
  }> => {
    const response = await api.get('/api/recommendations/history', {
      params: {
        session_id: sessionId,
        limit,
        offset,
      },
    })
    return response.data
  },

  submitFeedback: async (
    sessionId: string,
    recommendationId: number,
    liked?: boolean,
    alreadyKnew?: boolean
  ): Promise<{ message: string }> => {
    const response = await api.post('/api/recommendations/feedback', {
      recommendation_id: recommendationId,
      liked,
      already_knew: alreadyKnew,
    }, {
      params: { session_id: sessionId },
    })
    return response.data
  },

  getLibraryInfo: async (sessionId: string): Promise<{
    total_liked_songs: number
    message: string
  }> => {
    const response = await api.get('/api/recommendations/library-info', {
      params: { session_id: sessionId },
    })
    return response.data
  },

  getStatus: async (sessionId: string): Promise<{
    library_analyzed: boolean
    track_count: number
    cluster_count: number
    recommendation_count: number
    can_generate_recommendations: boolean
    needs_onboarding: boolean
    last_recommendation: string | null
    recommendations_today: number
    total_liked_songs: number
  }> => {
    const response = await api.get('/api/recommendations/status', {
      params: { session_id: sessionId },
    })
    return response.data
  },
}

// Progress API
export const progressApi = {
  getAnalysisProgress: async (sessionId: string): Promise<{
    status: string
    current_step: string
    progress_percentage: number
    tracks_processed: number
    total_tracks: number
    error_message?: string
    started_at?: string
    completed_at?: string
    updated_at?: string
  }> => {
    const response = await api.get(`/api/progress/analysis/${sessionId}`)
    return response.data
  },
}

// Analytics API
export const analyticsApi = {
  getOverview: async (sessionId: string): Promise<AnalyticsOverview> => {
    const response = await api.get('/api/analytics/overview', {
      params: { session_id: sessionId },
    })
    return response.data
  },

  getTasteEvolution: async (sessionId: string): Promise<{
    evolution: TasteEvolution[]
    total_periods: number
  }> => {
    const response = await api.get('/api/analytics/taste-evolution', {
      params: { session_id: sessionId },
    })
    return response.data
  },

  getClusterDetails: async (sessionId: string, clusterId: number): Promise<{
    cluster: any
    characteristics: any
    tracks: any[]
    recommendations: any[]
  }> => {
    const response = await api.get(`/api/analytics/clusters/${clusterId}`, {
      params: { session_id: sessionId },
    })
    return response.data
  },

  getRecommendationStats: async (sessionId: string): Promise<RecommendationStats> => {
    const response = await api.get('/api/analytics/recommendations-stats', {
      params: { session_id: sessionId },
    })
    return response.data
  },

  getAudioFeaturesDistribution: async (sessionId: string): Promise<AudioFeaturesDistribution> => {
    const response = await api.get('/api/analytics/audio-features-distribution', {
      params: { session_id: sessionId },
    })
    return response.data
  },
}

// Error handling interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized - redirect to login
      localStorage.removeItem('spotify_session_id')
      window.location.href = '/'
    }
    return Promise.reject(error)
  }
)

export default api
