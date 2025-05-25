import React from 'react'
import Layout from '../components/Layout'
import { Card, CardHeader } from '../components/Card'
import { BarChart3, TrendingUp, Users, Music } from 'lucide-react'

const AnalyticsPage: React.FC = () => {
  return (
    <Layout>
      <div className="p-6">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-spotify-white mb-2">
            Music Analytics
          </h1>
          <p className="text-spotify-gray">
            Deep insights into your music taste and listening patterns
          </p>
        </div>

        {/* Coming Soon Message */}
        <Card className="text-center py-12">
          <div className="flex justify-center mb-6">
            <div className="bg-spotify-green/20 rounded-full p-6">
              <BarChart3 className="h-16 w-16 text-spotify-green" />
            </div>
          </div>
          
          <h2 className="text-2xl font-bold text-spotify-white mb-4">
            Analytics Coming Soon
          </h2>
          
          <p className="text-spotify-gray mb-8 max-w-2xl mx-auto">
            We're building powerful analytics features to help you understand your music taste evolution, 
            cluster characteristics, and recommendation performance. This will include:
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            <div className="bg-spotify-black/50 rounded-lg p-6">
              <TrendingUp className="h-8 w-8 text-spotify-green mx-auto mb-3" />
              <h3 className="text-lg font-semibold text-spotify-white mb-2">
                Taste Evolution
              </h3>
              <p className="text-sm text-spotify-gray">
                Interactive timeline showing how your music preferences changed over time
              </p>
            </div>

            <div className="bg-spotify-black/50 rounded-lg p-6">
              <Users className="h-8 w-8 text-spotify-green mx-auto mb-3" />
              <h3 className="text-lg font-semibold text-spotify-white mb-2">
                Cluster Analysis
              </h3>
              <p className="text-sm text-spotify-gray">
                Detailed breakdown of your music taste clusters and their characteristics
              </p>
            </div>

            <div className="bg-spotify-black/50 rounded-lg p-6">
              <Music className="h-8 w-8 text-spotify-green mx-auto mb-3" />
              <h3 className="text-lg font-semibold text-spotify-white mb-2">
                Audio Features
              </h3>
              <p className="text-sm text-spotify-gray">
                Distribution charts for energy, valence, danceability, and more
              </p>
            </div>
          </div>

          <div className="mt-8">
            <button
              onClick={() => window.location.href = '/dashboard'}
              className="btn-primary"
            >
              Back to Dashboard
            </button>
          </div>
        </Card>
      </div>
    </Layout>
  )
}

export default AnalyticsPage
