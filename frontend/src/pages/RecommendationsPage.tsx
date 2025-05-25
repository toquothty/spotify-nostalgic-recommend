import React, { useState, useEffect } from 'react'
import Layout from '../components/Layout'
import RecommendationCard from '../components/RecommendationCard'
import { Card, CardHeader } from '../components/Card'
import { useAuth } from '../contexts/AuthContext'
import { recommendationsApi } from '../services/api'
import { Recommendation } from '../types'
import { RefreshCw, Sparkles, Clock, TrendingUp } from 'lucide-react'

const RecommendationsPage: React.FC = () => {
  const { sessionId } = useAuth()
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [recommendationType, setRecommendationType] = useState<'cluster' | 'nostalgia'>('cluster')
  const [recommendationLimit, setRecommendationLimit] = useState(5)

  useEffect(() => {
    if (sessionId) {
      loadRecommendationHistory()
    }
  }, [sessionId])

  const loadRecommendationHistory = async () => {
    if (!sessionId) return

    try {
      setIsLoading(true)
      setError(null)
      const response = await recommendationsApi.getRecommendationHistory(sessionId, 20)
      setRecommendations(response.recommendations)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load recommendations')
    } finally {
      setIsLoading(false)
    }
  }

  const generateRecommendations = async () => {
    if (!sessionId) return

    try {
      setIsGenerating(true)
      setError(null)
      
      const response = await recommendationsApi.generateRecommendations(
        sessionId,
        recommendationType,
        recommendationLimit
      )
      
      // Add new recommendations to the top of the list
      setRecommendations(prev => [...response.recommendations, ...prev])
      
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate recommendations')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleFeedback = async (recommendationId: number, liked?: boolean, alreadyKnew?: boolean) => {
    if (!sessionId) return

    try {
      await recommendationsApi.submitFeedback(sessionId, recommendationId, liked, alreadyKnew)
      
      // Update the recommendation in the list to show feedback was submitted
      setRecommendations(prev =>
        prev.map(rec =>
          rec.id === recommendationId
            ? { ...rec, user_liked: liked ?? null, user_already_knew: alreadyKnew ?? null }
            : rec
        )
      )
    } catch (err: any) {
      console.error('Failed to submit feedback:', err)
      // Could show a toast notification here
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60))
    
    if (diffInHours < 1) return 'Just now'
    if (diffInHours < 24) return `${diffInHours} hours ago`
    const diffInDays = Math.floor(diffInHours / 24)
    return `${diffInDays} days ago`
  }

  const groupRecommendationsByDate = (recs: Recommendation[]) => {
    const groups: { [key: string]: Recommendation[] } = {}
    
    recs.forEach(rec => {
      const date = new Date(rec.created_at).toDateString()
      if (!groups[date]) {
        groups[date] = []
      }
      groups[date].push(rec)
    })
    
    return groups
  }

  const groupedRecommendations = groupRecommendationsByDate(recommendations)

  return (
    <Layout>
      <div className="p-6">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-spotify-white mb-2">
            Your Recommendations 🎵
          </h1>
          <p className="text-spotify-gray">
            Discover new music based on your taste clusters and nostalgic favorites
          </p>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-6 p-4 bg-red-900/20 border border-red-500/20 rounded-lg">
            <p className="text-red-400">{error}</p>
          </div>
        )}

        {/* Generate New Recommendations */}
        <Card className="mb-8">
          <CardHeader
            title="Generate New Recommendations"
            subtitle="Get personalized music recommendations based on your taste"
          />
          
          <div className="space-y-4">
            {/* Recommendation Type */}
            <div>
              <label className="block text-sm font-medium text-spotify-white mb-2">
                Recommendation Type
              </label>
              <div className="flex space-x-4">
                <button
                  onClick={() => setRecommendationType('cluster')}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-lg border transition-colors ${
                    recommendationType === 'cluster'
                      ? 'bg-spotify-green/20 border-spotify-green text-spotify-green'
                      : 'bg-spotify-black border-spotify-gray/30 text-spotify-gray hover:text-spotify-white'
                  }`}
                >
                  <TrendingUp className="h-4 w-4" />
                  <span>Based on Your Taste</span>
                </button>
                
                <button
                  onClick={() => setRecommendationType('nostalgia')}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-lg border transition-colors ${
                    recommendationType === 'nostalgia'
                      ? 'bg-spotify-green/20 border-spotify-green text-spotify-green'
                      : 'bg-spotify-black border-spotify-gray/30 text-spotify-gray hover:text-spotify-white'
                  }`}
                >
                  <Clock className="h-4 w-4" />
                  <span>Nostalgic Hits</span>
                </button>
              </div>
            </div>

            {/* Number of Recommendations */}
            <div>
              <label className="block text-sm font-medium text-spotify-white mb-2">
                Number of Recommendations
              </label>
              <select
                value={recommendationLimit}
                onChange={(e) => setRecommendationLimit(Number(e.target.value))}
                className="bg-spotify-black border border-spotify-gray/30 rounded-lg px-3 py-2 text-spotify-white focus:outline-none focus:border-spotify-green"
              >
                <option value={5}>5 recommendations</option>
                <option value={10}>10 recommendations</option>
                <option value={15}>15 recommendations</option>
                <option value={20}>20 recommendations</option>
                <option value={30}>30 recommendations</option>
              </select>
            </div>

            {/* Generate Button */}
            <button
              onClick={generateRecommendations}
              disabled={isGenerating}
              className="flex items-center space-x-2 bg-spotify-green hover:bg-spotify-green/80 disabled:bg-spotify-gray disabled:cursor-not-allowed text-black font-semibold px-6 py-3 rounded-lg transition-colors"
            >
              {isGenerating ? (
                <>
                  <RefreshCw className="h-5 w-5 animate-spin" />
                  <span>Generating...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-5 w-5" />
                  <span>Generate Recommendations</span>
                </>
              )}
            </button>
          </div>
        </Card>

        {/* Recommendations Display */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="h-8 w-8 animate-spin text-spotify-green" />
            <span className="ml-3 text-spotify-gray">Loading recommendations...</span>
          </div>
        ) : recommendations.length === 0 ? (
          <Card>
            <div className="text-center py-12">
              <Sparkles className="h-16 w-16 text-spotify-gray mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-spotify-white mb-2">
                No Recommendations Yet
              </h3>
              <p className="text-spotify-gray mb-6">
                Generate your first set of personalized recommendations to get started!
              </p>
            </div>
          </Card>
        ) : (
          <div className="space-y-8">
            {Object.entries(groupedRecommendations).map(([date, recs]) => (
              <div key={date}>
                <h2 className="text-lg font-semibold text-spotify-white mb-4">
                  {formatDate(recs[0].created_at)} • {recs.length} recommendations
                </h2>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6">
                  {recs.map((recommendation) => (
                    <RecommendationCard
                      key={recommendation.id}
                      recommendation={{
                        id: recommendation.id,
                        spotify_track_id: recommendation.spotify_track_id,
                        track_name: recommendation.track_name,
                        artist_name: recommendation.artist_name,
                        album_name: recommendation.album_name || undefined,
                        preview_url: recommendation.preview_url || undefined,
                        external_url: recommendation.external_url || undefined,
                        image_url: recommendation.image_url || undefined,
                        confidence_score: recommendation.confidence_score || undefined,
                        source_cluster_id: recommendation.source_cluster_id || undefined,
                      }}
                      onFeedback={handleFeedback}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  )
}

export default RecommendationsPage
