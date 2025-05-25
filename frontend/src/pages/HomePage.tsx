import React from 'react'
import { useAuth } from '../contexts/AuthContext'
import { Music, Sparkles, TrendingUp } from 'lucide-react'

const HomePage: React.FC = () => {
  const { login, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-spotify-green mx-auto mb-4"></div>
          <p className="text-spotify-gray">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-spotify-black via-gray-900 to-spotify-black">
      {/* Header */}
      <header className="container mx-auto px-6 py-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Music className="h-8 w-8 text-spotify-green" />
            <h1 className="text-2xl font-bold text-spotify-white">Nostalgic Recommender</h1>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="container mx-auto px-6 py-16">
        <div className="text-center max-w-4xl mx-auto">
          <h2 className="text-5xl md:text-6xl font-bold text-spotify-white mb-6">
            Rediscover Your
            <span className="text-spotify-green"> Musical Journey</span>
          </h2>
          
          <p className="text-xl text-spotify-gray mb-12 max-w-2xl mx-auto">
            Uncover forgotten favorites and nostalgic hits from your formative years. 
            Let AI analyze your music taste and recommend songs that will take you back in time.
          </p>

          <button
            onClick={login}
            className="btn-primary text-lg px-8 py-4 mb-16"
          >
            Connect with Spotify
          </button>

          {/* Features */}
          <div className="grid md:grid-cols-3 gap-8 mt-16">
            <div className="card text-center">
              <div className="bg-spotify-green/20 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                <Sparkles className="h-8 w-8 text-spotify-green" />
              </div>
              <h3 className="text-xl font-semibold text-spotify-white mb-3">Smart Analysis</h3>
              <p className="text-spotify-gray">
                AI-powered clustering analyzes your music taste to understand your unique preferences
              </p>
            </div>

            <div className="card text-center">
              <div className="bg-spotify-green/20 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                <Music className="h-8 w-8 text-spotify-green" />
              </div>
              <h3 className="text-xl font-semibold text-spotify-white mb-3">Forgotten Favorites</h3>
              <p className="text-spotify-gray">
                Discover songs that match your taste but somehow slipped through the cracks
              </p>
            </div>

            <div className="card text-center">
              <div className="bg-spotify-green/20 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                <TrendingUp className="h-8 w-8 text-spotify-green" />
              </div>
              <h3 className="text-xl font-semibold text-spotify-white mb-3">Nostalgic Hits</h3>
              <p className="text-spotify-gray">
                Relive your formative years with chart-toppers from when you were 12-18 years old
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="container mx-auto px-6 py-8 text-center text-spotify-gray">
        <p>Built with ❤️ for music lovers everywhere</p>
      </footer>
    </div>
  )
}

export default HomePage
