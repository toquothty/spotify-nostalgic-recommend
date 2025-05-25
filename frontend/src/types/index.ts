export interface User {
  id: number
  spotify_id: string
  display_name: string | null
  email: string | null
  country: string | null
  date_of_birth: string | null
  needs_onboarding: boolean
}

export interface Track {
  id: number
  spotify_id: string
  name: string
  artist_name: string
  album_name: string | null
  duration_ms: number | null
  popularity: number | null
  explicit: boolean
  preview_url: string | null
  external_url: string | null
  image_url: string | null
  added_at: string | null
  release_date: string | null
  cluster_id: number | null
}

export interface Recommendation {
  id: number
  spotify_track_id: string
  track_name: string
  artist_name: string
  album_name: string | null
  preview_url: string | null
  external_url: string | null
  image_url: string | null
  recommendation_type: string
  source_cluster_id: number | null
  confidence_score: number | null
  user_liked: boolean | null
  user_already_knew: boolean | null
  created_at: string
}

export interface Cluster {
  id: number
  cluster_id: number
  centroid_data: Record<string, number>
  track_count: number
  created_at: string
  characteristics?: {
    centroid: Record<string, number>
    track_count: number
    sample_tracks: Array<{
      name: string
      artist: string
      spotify_id: string
    }>
    dominant_features: string[]
    description: string
  }
}

export interface AnalyticsOverview {
  total_tracks: number
  clusters: Cluster[]
  top_genres: Array<{ name: string; count: number }>
  audio_features_summary: Record<string, number>
  formative_years: {
    start_year: number
    end_year: number
    years: number[]
  } | null
  cluster_characteristics: Record<number, any>
}

export interface TasteEvolution {
  period: string
  track_count: number
  avg_features: Record<string, number>
  top_genres: string[]
  date_range: {
    start: string
    end: string
  }
}

export interface RecommendationStats {
  total_recommendations: number
  liked_count: number
  disliked_count: number
  already_knew_count: number
  pending_feedback: number
  like_rate: number
  by_type: Record<string, { count: number; liked: number }>
  by_cluster: Record<number, { count: number; liked: number }>
}

export interface AudioFeaturesDistribution {
  distributions: Record<string, {
    mean: number
    min: number
    max: number
    histogram: Array<{
      bin_start: number
      bin_end: number
      count: number
      percentage: number
    }>
    total_tracks: number
  }>
  total_tracks_analyzed: number
}
