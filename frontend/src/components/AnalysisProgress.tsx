import React from 'react'
import { CheckCircle, AlertCircle, Loader2, Music } from 'lucide-react'

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

interface AnalysisProgressProps {
  progress: AnalysisProgress | null
  isVisible: boolean
}

const AnalysisProgress: React.FC<AnalysisProgressProps> = ({ progress, isVisible }) => {
  if (!isVisible || !progress) return null

  const getStatusIcon = () => {
    switch (progress.status) {
      case 'completed':
        return <CheckCircle className="h-6 w-6 text-spotify-green" />
      case 'failed':
        return <AlertCircle className="h-6 w-6 text-red-500" />
      default:
        return <Loader2 className="h-6 w-6 text-spotify-green animate-spin" />
    }
  }

  const getStatusColor = () => {
    switch (progress.status) {
      case 'completed':
        return 'border-spotify-green bg-spotify-green/10'
      case 'failed':
        return 'border-red-500 bg-red-500/10'
      default:
        return 'border-spotify-green bg-spotify-green/10'
    }
  }

  const formatTime = (isoString: string | undefined) => {
    if (!isoString) return ''
    const date = new Date(isoString)
    return date.toLocaleTimeString()
  }

  const getEstimatedTimeRemaining = () => {
    if (progress.status === 'completed' || progress.status === 'failed') return null
    if (progress.progress_percentage === 0) return null

    const elapsed = progress.started_at ? 
      (new Date().getTime() - new Date(progress.started_at).getTime()) / 1000 : 0
    
    if (elapsed < 10) return null // Don't show estimate for first 10 seconds

    const estimatedTotal = (elapsed / progress.progress_percentage) * 100
    const remaining = Math.max(0, estimatedTotal - elapsed)
    
    if (remaining < 60) {
      return `~${Math.round(remaining)}s remaining`
    } else {
      return `~${Math.round(remaining / 60)}m remaining`
    }
  }

  return (
    <div className={`fixed top-4 right-4 z-50 w-96 rounded-lg border-2 p-4 shadow-lg backdrop-blur-sm ${getStatusColor()}`}>
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0 mt-1">
          {getStatusIcon()}
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-spotify-white">
              Library Analysis
            </h3>
            {progress.status !== 'completed' && progress.status !== 'failed' && (
              <span className="text-xs text-spotify-gray">
                {progress.progress_percentage}%
              </span>
            )}
          </div>

          <p className="text-sm text-spotify-white mb-3">
            {progress.current_step}
          </p>

          {progress.status === 'failed' && progress.error_message && (
            <p className="text-sm text-red-400 mb-3">
              {progress.error_message}
            </p>
          )}

          {/* Progress Bar */}
          {progress.status !== 'failed' && (
            <div className="mb-3">
              <div className="w-full bg-spotify-black/50 rounded-full h-2">
                <div
                  className="bg-spotify-green h-2 rounded-full transition-all duration-300 ease-out"
                  style={{ width: `${progress.progress_percentage}%` }}
                />
              </div>
            </div>
          )}

          {/* Stats */}
          <div className="flex items-center justify-between text-xs text-spotify-gray">
            <div className="flex items-center space-x-4">
              {progress.total_tracks > 0 && (
                <span className="flex items-center space-x-1">
                  <Music className="h-3 w-3" />
                  <span>{progress.tracks_processed.toLocaleString()} / {progress.total_tracks.toLocaleString()}</span>
                </span>
              )}
              
              {progress.started_at && (
                <span>Started {formatTime(progress.started_at)}</span>
              )}
            </div>

            <div>
              {getEstimatedTimeRemaining()}
            </div>
          </div>

          {/* Completion message */}
          {progress.status === 'completed' && (
            <div className="mt-2 text-xs text-spotify-green">
              ✓ Analysis completed at {formatTime(progress.completed_at)}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default AnalysisProgress
