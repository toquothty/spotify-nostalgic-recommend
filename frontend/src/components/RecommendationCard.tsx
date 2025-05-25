import React, { useState, useRef } from 'react'
import { Play, Pause, Heart, X, ExternalLink } from 'lucide-react'

interface RecommendationCardProps {
  recommendation: {
    id: number
    spotify_track_id: string
    track_name: string
    artist_name: string
    album_name?: string
    preview_url?: string
    external_url?: string
    image_url?: string
    confidence_score?: number
    source_cluster_id?: number
  }
  onFeedback: (recommendationId: number, liked?: boolean, alreadyKnew?: boolean) => void
}

const RecommendationCard: React.FC<RecommendationCardProps> = ({
  recommendation,
  onFeedback,
}) => {
  const [isPlaying, setIsPlaying] = useState(false)
  const [hasGivenFeedback, setHasGivenFeedback] = useState(false)
  const audioRef = useRef<HTMLAudioElement>(null)

  const handlePlayPause = () => {
    if (!recommendation.preview_url || !audioRef.current) return

    if (isPlaying) {
      audioRef.current.pause()
      setIsPlaying(false)
    } else {
      audioRef.current.play()
      setIsPlaying(true)
    }
  }

  const handleAudioEnded = () => {
    setIsPlaying(false)
  }

  const handleFeedback = (liked?: boolean, alreadyKnew?: boolean) => {
    onFeedback(recommendation.id, liked, alreadyKnew)
    setHasGivenFeedback(true)
  }

  const openInSpotify = () => {
    if (recommendation.external_url) {
      window.open(recommendation.external_url, '_blank')
    }
  }

  return (
    <div className="bg-spotify-black/50 rounded-lg p-4 border border-spotify-gray/20 hover:border-spotify-green/30 transition-all duration-200">
      {/* Track Image */}
      <div className="relative mb-4">
        <img
          src={recommendation.image_url || '/placeholder-album.png'}
          alt={`${recommendation.track_name} album cover`}
          className="w-full aspect-square object-cover rounded-lg"
          onError={(e) => {
            e.currentTarget.src = '/placeholder-album.png'
          }}
        />
        
        {/* Play/Pause Button Overlay */}
        {recommendation.preview_url && (
          <button
            onClick={handlePlayPause}
            className="absolute inset-0 flex items-center justify-center bg-black/50 opacity-0 hover:opacity-100 transition-opacity duration-200 rounded-lg"
          >
            <div className="bg-spotify-green rounded-full p-3 hover:scale-110 transition-transform">
              {isPlaying ? (
                <Pause className="h-6 w-6 text-black" />
              ) : (
                <Play className="h-6 w-6 text-black ml-1" />
              )}
            </div>
          </button>
        )}

        {/* Confidence Score Badge */}
        {recommendation.confidence_score && (
          <div className="absolute top-2 right-2 bg-spotify-green/90 text-black text-xs font-bold px-2 py-1 rounded">
            {Math.round(recommendation.confidence_score * 100)}%
          </div>
        )}
      </div>

      {/* Track Info */}
      <div className="mb-4">
        <h3 className="text-spotify-white font-semibold text-lg mb-1 line-clamp-2">
          {recommendation.track_name}
        </h3>
        <p className="text-spotify-gray text-sm mb-1">
          {recommendation.artist_name}
        </p>
        {recommendation.album_name && (
          <p className="text-spotify-gray/70 text-xs">
            {recommendation.album_name}
          </p>
        )}
      </div>

      {/* Audio Element */}
      {recommendation.preview_url && (
        <audio
          ref={audioRef}
          src={recommendation.preview_url}
          onEnded={handleAudioEnded}
          preload="none"
        />
      )}

      {/* Action Buttons */}
      <div className="flex items-center justify-between">
        {!hasGivenFeedback ? (
          <div className="flex space-x-2">
            <button
              onClick={() => handleFeedback(true)}
              className="flex items-center space-x-1 bg-spotify-green/20 hover:bg-spotify-green/30 text-spotify-green px-3 py-2 rounded-lg text-sm font-medium transition-colors"
              title="Like this recommendation"
            >
              <Heart className="h-4 w-4" />
              <span>Like</span>
            </button>
            
            <button
              onClick={() => handleFeedback(false)}
              className="flex items-center space-x-1 bg-red-500/20 hover:bg-red-500/30 text-red-400 px-3 py-2 rounded-lg text-sm font-medium transition-colors"
              title="Don't like this recommendation"
            >
              <X className="h-4 w-4" />
              <span>Pass</span>
            </button>
            
            <button
              onClick={() => handleFeedback(undefined, true)}
              className="flex items-center space-x-1 bg-spotify-gray/20 hover:bg-spotify-gray/30 text-spotify-gray px-3 py-2 rounded-lg text-sm font-medium transition-colors"
              title="Already know this song"
            >
              <span>Know It</span>
            </button>
          </div>
        ) : (
          <div className="text-spotify-green text-sm font-medium">
            ✓ Feedback submitted
          </div>
        )}

        {/* Open in Spotify */}
        <button
          onClick={openInSpotify}
          className="flex items-center space-x-1 text-spotify-gray hover:text-spotify-white transition-colors"
          title="Open in Spotify"
        >
          <ExternalLink className="h-4 w-4" />
        </button>
      </div>

      {/* Cluster Info */}
      {recommendation.source_cluster_id !== undefined && (
        <div className="mt-3 pt-3 border-t border-spotify-gray/20">
          <p className="text-xs text-spotify-gray">
            From your taste cluster #{recommendation.source_cluster_id}
          </p>
        </div>
      )}
    </div>
  )
}

export default RecommendationCard
