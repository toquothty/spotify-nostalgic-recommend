import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../components/Layout'
import { Card, CardHeader, StatCard, ActionCard } from '../components/Card'
import AnalysisProgress from '../components/AnalysisProgress'
import { useAuth } from '../contexts/AuthContext'
import { useLibraryAnalysis } from '../hooks/useLibraryAnalysis'
import { useAnalysisProgress } from '../hooks/useAnalysisProgress'
import { 
  Music, 
  Sparkles, 
  TrendingUp, 
  Clock, 
  Users, 
  Heart,
  RefreshCw,
  Settings
} from 'lucide-react'

const DashboardPage: React.FC = () => {
  const { user, sessionId } = useAuth()
  const navigate = useNavigate()
  const { status, isLoading, isAnalyzing, error, analyzeLibrary } = useLibraryAnalysis()
  const { progress, startPolling } = useAnalysisProgress(sessionId)
  const [selectedTrackLimit, setSelectedTrackLimit] = useState(1000)

  const handleAnalyzeLibrary = async () => {
    const result = await analyzeLibrary(selectedTrackLimit)
    if (result) {
      // Start polling for progress updates
      startPolling()
      console.log('Analysis started:', result)
    }
  }

  const handleGenerateRecommendations = () => {
    navigate('/recommendations')
  }

  const getWelcomeMessage = () => {
    const hour = new Date().getHours()
    if (hour < 12) return 'Good morning'
    if (hour < 18) return 'Good afternoon'
    return 'Good evening'
  }

  const formatLastRecommendation = (dateString: string | null) => {
    if (!dateString) return 'Never'
    const date = new Date(dateString)
    const now = new Date()
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60))
    
    if (diffInHours < 1) return 'Less than an hour ago'
    if (diffInHours < 24) return `${diffInHours} hours ago`
    const diffInDays = Math.floor(diffInHours / 24)
    return `${diffInDays} days ago`
  }

  // Show progress overlay when analysis is running
  const isAnalysisRunning = progress && ['starting', 'fetching_tracks', 'getting_features', 'clustering'].includes(progress.status)
  const showProgress = Boolean(isAnalysisRunning)

  return (
    <Layout>
      <div className="p-6">
        {/* Real-time Progress Overlay */}
        <AnalysisProgress 
          progress={progress} 
          isVisible={showProgress} 
        />

        {/* Welcome Section */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-spotify-white mb-2">
            {getWelcomeMessage()}, {user?.display_name || 'Music Lover'}! 👋
          </h1>
          <p className="text-spotify-gray">
            Ready to discover your forgotten favorites and nostalgic hits?
          </p>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-6 p-4 bg-red-900/20 border border-red-500/20 rounded-lg">
            <p className="text-red-400">{error}</p>
          </div>
        )}

        {/* Progress Error Display */}
        {progress?.status === 'failed' && progress.error_message && (
          <div className="mb-6 p-4 bg-red-900/20 border border-red-500/20 rounded-lg">
            <p className="text-red-400">Analysis failed: {progress.error_message}</p>
          </div>
        )}

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            title="Tracks Analyzed"
            value={progress?.tracks_processed || status?.track_count || 0}
            subtitle={status?.library_analyzed ? 'Analysis complete' : 'Not analyzed yet'}
            icon={<Music className="h-6 w-6" />}
          />
          
          <StatCard
            title="Music Clusters"
            value={status?.cluster_count || 0}
            subtitle="Taste profiles discovered"
            icon={<Users className="h-6 w-6" />}
          />
          
          <StatCard
            title="Recommendations"
            value={status?.recommendation_count || 0}
            subtitle="Songs discovered"
            icon={<Heart className="h-6 w-6" />}
          />
          
          <StatCard
            title="Today's Recommendations"
            value={`${status?.recommendations_today || 0}/100`}
            subtitle="Daily limit"
            icon={<Clock className="h-6 w-6" />}
          />
        </div>

        {/* Main Actions */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Library Analysis */}
          <ActionCard
            title="Analyze Your Music Library"
            description={
              progress?.status === 'completed' || status?.library_analyzed
                ? `Your library has been analyzed! ${progress?.tracks_processed || status?.track_count || 0} tracks organized into ${status?.cluster_count || 0} taste clusters.`
                : isAnalysisRunning
                ? `Analysis in progress: ${progress.current_step}`
                : "Let AI analyze your Spotify library to understand your music taste and create personalized clusters."
            }
            buttonText={
              isAnalysisRunning
                ? "Analyzing..."
                : status?.library_analyzed || progress?.status === 'completed'
                ? "Re-analyze Library"
                : "Start Analysis"
            }
            onAction={handleAnalyzeLibrary}
            isLoading={Boolean(isAnalyzing || isAnalysisRunning)}
            disabled={Boolean(isLoading || isAnalysisRunning)}
            icon={<Sparkles className="h-6 w-6" />}
          />

          {/* Generate Recommendations */}
          <ActionCard
            title="Get New Recommendations"
            description={
              status?.can_generate_recommendations
                ? `Discover new songs based on your taste clusters. Last recommendations: ${formatLastRecommendation(status.last_recommendation)}`
                : "Complete library analysis first to unlock personalized recommendations."
            }
            buttonText="Generate Recommendations"
            onAction={handleGenerateRecommendations}
            disabled={!status?.can_generate_recommendations || (status?.recommendations_today >= 100)}
            icon={<TrendingUp className="h-6 w-6" />}
          />
        </div>

        {/* Analysis Configuration */}
        {!status?.library_analyzed && progress?.status !== 'completed' && (
          <Card className="mb-8">
            <CardHeader
              title="Analysis Settings"
              subtitle="Configure how many tracks to analyze from your library"
            />
            <div className="space-y-4">
              {/* Show total liked songs count */}
              {status?.total_liked_songs !== undefined && (
                <div className="bg-spotify-green/10 border border-spotify-green/20 rounded-lg p-4">
                  <div className="flex items-center space-x-2">
                    <Music className="h-5 w-5 text-spotify-green" />
                    <span className="text-sm font-medium text-spotify-green">
                      Your Spotify Library
                    </span>
                  </div>
                  <p className="text-spotify-white mt-1">
                    You have <span className="font-bold text-spotify-green">{status.total_liked_songs.toLocaleString()}</span> liked songs
                  </p>
                </div>
              )}
              
              <div>
                <label className="block text-sm font-medium text-spotify-white mb-2">
                  Number of tracks to analyze
                </label>
                <select
                  value={selectedTrackLimit}
                  onChange={(e) => setSelectedTrackLimit(Number(e.target.value))}
                  className="bg-spotify-black border border-spotify-gray/30 rounded-lg px-3 py-2 text-spotify-white focus:outline-none focus:border-spotify-green"
                  disabled={Boolean(isAnalysisRunning)}
                >
                  <option value={500}>500 tracks (Quick analysis)</option>
                  <option value={1000}>1,000 tracks (Recommended)</option>
                  <option value={2000}>2,000 tracks (Comprehensive)</option>
                  <option value={-1}>All tracks (Complete analysis)</option>
                </select>
              </div>
              <p className="text-sm text-spotify-gray">
                More tracks provide better accuracy but take longer to process. 
                We recommend starting with 1,000 tracks for the best balance.
                {status?.total_liked_songs && selectedTrackLimit !== -1 && (
                  <span className="block mt-1">
                    This will analyze {Math.min(selectedTrackLimit, status.total_liked_songs).toLocaleString()} of your {status.total_liked_songs.toLocaleString()} liked songs.
                  </span>
                )}
              </p>
            </div>
          </Card>
        )}

        {/* Quick Stats */}
        {(status?.library_analyzed || progress?.status === 'completed') && (
          <Card>
            <CardHeader
              title="Library Overview"
              subtitle="Your music taste at a glance"
              action={
                <button
                  onClick={() => navigate('/analytics')}
                  className="text-spotify-green hover:text-spotify-green/80 text-sm font-medium"
                >
                  View Analytics →
                </button>
              }
            />
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center p-4 bg-spotify-black/50 rounded-lg">
                <Music className="h-8 w-8 text-spotify-green mx-auto mb-2" />
                <p className="text-2xl font-bold text-spotify-white">{progress?.tracks_processed || status?.track_count || 0}</p>
                <p className="text-sm text-spotify-gray">Tracks Analyzed</p>
              </div>
              <div className="text-center p-4 bg-spotify-black/50 rounded-lg">
                <Users className="h-8 w-8 text-spotify-green mx-auto mb-2" />
                <p className="text-2xl font-bold text-spotify-white">{status?.cluster_count || 0}</p>
                <p className="text-sm text-spotify-gray">Taste Clusters</p>
              </div>
              <div className="text-center p-4 bg-spotify-black/50 rounded-lg">
                <Heart className="h-8 w-8 text-spotify-green mx-auto mb-2" />
                <p className="text-2xl font-bold text-spotify-white">{status?.recommendation_count || 0}</p>
                <p className="text-sm text-spotify-gray">Recommendations</p>
              </div>
            </div>
          </Card>
        )}
      </div>
    </Layout>
  )
}

export default DashboardPage
