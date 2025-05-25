# Spotify Nostalgic Recommender

A full-stack web application that helps users rediscover forgotten songs and find new favorites based on their Spotify Liked Songs library. The app analyzes your music taste using machine learning and shows songs from your formative years (ages 12-18) while visualizing how your music taste evolved over time.

## Features

### 🎵 Core Functionality
- **Smart Music Analysis**: AI-powered K-means clustering analyzes your music taste patterns
- **Forgotten Favorites**: Discover songs that match your taste but somehow slipped through the cracks
- **Nostalgic Hits**: Relive your formative years with chart-toppers from when you were 12-18 years old
- **Taste Evolution**: Interactive timeline showing how your music preferences changed over time

### 🔐 Authentication
- Spotify OAuth 2.0 with PKCE (Authorization Code + PKCE)
- Secure session management
- Required scopes: `user-library-read`, `user-library-modify`, `user-read-private`, `user-read-email`

### 📊 Analytics & Insights
- **Music Taste Clusters**: Visualize your music grouped into 10 distinct taste clusters
- **Audio Features Analysis**: Deep dive into acousticness, energy, valence, and more
- **Recommendation Statistics**: Track your likes, dislikes, and discovery rate
- **Genre Evolution**: See how your preferred artists and genres changed over time

### 🎯 Smart Recommendations
- **Cluster-based**: Recommendations based on your music taste clusters
- **Nostalgia Mode**: Billboard hits from your formative years filtered by taste similarity
- **Rate Limiting**: 4-hour cooldown OR max 4 recommendations per day
- **Feedback System**: "Like" and "Already know this song" buttons to improve future recommendations

## Tech Stack

### Backend
- **Python 3.11** with FastAPI
- **Machine Learning**: scikit-learn (K-means clustering), pandas, numpy
- **Database**: SQLite (PostgreSQL-ready)
- **APIs**: Spotify Web API, Billboard chart scraping
- **Testing**: pytest with 80% coverage minimum

### Frontend
- **React 18** with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS with Spotify-inspired design
- **Charts**: Chart.js for data visualization
- **Icons**: Lucide React

### Infrastructure
- **Containerization**: Docker Compose for development
- **Code Quality**: Black, Ruff, isort with pre-commit hooks
- **Documentation**: OpenAPI/Swagger auto-generated docs

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Spotify Developer Account

### 1. Clone the Repository
```bash
git clone <repository-url>
cd spotify-nostalgic-recommend
```

### 2. Set Up Environment Variables
```bash
# Copy the template and fill in your Spotify API credentials
cp .env.template .env
```

Edit `.env` with your Spotify API credentials:
```env
SPOTIFY_CLIENT_ID=your_spotify_client_id_here
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret_here
SPOTIFY_REDIRECT_URI=http://127.0.0.1:3000/callback
SECRET_KEY=your_secret_key_for_session_encryption
```

### 3. Start the Application
```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

### 4. Access the Application
- **Frontend**: http://127.0.0.1:3000
- **Backend API**: http://127.0.0.1:8000
- **API Documentation**: http://127.0.0.1:8000/docs

## How It Works

### 1. Authentication Flow
1. User clicks "Connect with Spotify"
2. Redirected to Spotify OAuth with PKCE
3. User authorizes the application
4. Redirected back with authorization code
5. Backend exchanges code for access/refresh tokens
6. User completes onboarding (date of birth required)

### 2. Music Analysis Pipeline
1. **Data Collection**: Fetch user's Liked Songs (default: 1000 tracks)
2. **Feature Extraction**: Get audio features for each track (tempo, energy, valence, etc.)
3. **Clustering**: Apply K-means clustering (k=10) on normalized features
4. **Storage**: Store tracks, features, and cluster assignments in database

### 3. Recommendation Generation
#### Cluster-based Recommendations
- Use cluster centroids as target audio features
- Generate recommendations via Spotify API
- Filter out already-liked songs
- Score by confidence and popularity

#### Nostalgia Recommendations
- Calculate formative years (ages 12-18) from date of birth
- Scrape Billboard Hot 100 data for those years
- Filter by audio similarity to user's taste clusters
- Match Billboard tracks with Spotify catalog

### 4. Analytics & Visualization
- **Taste Evolution**: Group tracks by quarter, analyze feature trends
- **Cluster Characteristics**: Generate human-readable cluster descriptions
- **Audio Features Distribution**: Create histograms for each audio feature
- **Recommendation Performance**: Track user feedback and success rates

## API Endpoints

### Authentication
- `GET /api/auth/login` - Initiate Spotify OAuth
- `GET /api/auth/callback` - Handle OAuth callback
- `POST /api/auth/onboarding` - Complete user onboarding
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/logout` - Logout user

### Recommendations
- `POST /api/recommendations/analyze-library` - Start library analysis
- `GET /api/recommendations/generate` - Generate new recommendations
- `GET /api/recommendations/history` - Get recommendation history
- `POST /api/recommendations/feedback` - Submit recommendation feedback
- `GET /api/recommendations/status` - Get analysis status

### Analytics
- `GET /api/analytics/overview` - Get analytics overview
- `GET /api/analytics/taste-evolution` - Get taste evolution timeline
- `GET /api/analytics/clusters/{id}` - Get cluster details
- `GET /api/analytics/recommendations-stats` - Get recommendation statistics
- `GET /api/analytics/audio-features-distribution` - Get audio features distribution

## Development

### Backend Development
```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Run tests
pytest

# Format code
black .
ruff check .
isort .

# Run development server
uvicorn app.main:app --reload
```

### Frontend Development
```bash
# Install dependencies
cd frontend
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Lint code
npm run lint
```

### Database Schema
The application uses SQLite by default with the following main tables:
- `users` - User profiles and preferences
- `tracks` - User's liked songs with audio features
- `user_clusters` - K-means cluster centroids and metadata
- `recommendations` - Generated recommendations with user feedback
- `billboard_charts` - Historical Billboard chart data
- `user_sessions` - Session management and rate limiting

## Configuration

### Environment Variables
- `SPOTIFY_CLIENT_ID` - Your Spotify app client ID
- `SPOTIFY_CLIENT_SECRET` - Your Spotify app client secret
- `SPOTIFY_REDIRECT_URI` - OAuth redirect URI
- `SECRET_KEY` - Session encryption key
- `DATABASE_URL` - Database connection string
- `BILLBOARD_CACHE_HOURS` - Billboard data cache duration (default: 24)
- `MAX_RECOMMENDATIONS_PER_DAY` - Daily recommendation limit (default: 4)
- `RECOMMENDATION_COOLDOWN_HOURS` - Cooldown between recommendations (default: 4)

### Spotify App Setup
1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Add redirect URI: `http://127.0.0.1:3000/callback`
4. Copy Client ID and Client Secret to `.env`

## Deployment

The application is designed for easy deployment with Docker:

```bash
# Production build
docker-compose -f docker-compose.prod.yml up --build

# Or deploy to your preferred platform
# (AWS, GCP, Azure, Heroku, etc.)
```

For production deployment:
1. Update environment variables for production
2. Use PostgreSQL instead of SQLite
3. Set up proper SSL/TLS certificates
4. Configure domain and update Spotify redirect URI
5. Set up monitoring and logging

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass and code is formatted
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Spotify Web API for music data
- Billboard.com for historical chart data
- The open-source community for the amazing tools and libraries
