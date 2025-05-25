import React, { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

const CallbackPage: React.FC = () => {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { updateUser } = useAuth()
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing')
  const [error, setError] = useState<string>('')

  useEffect(() => {
    const handleCallback = async () => {
      const error = searchParams.get('error')
      const sessionId = searchParams.get('session')

      if (error) {
        setStatus('error')
        setError(`Authorization failed: ${error}`)
        return
      }

      try {
        // Check if we have a session ID in the URL parameters (from backend redirect)
        if (sessionId) {
          // Store session ID in localStorage
          localStorage.setItem('spotify_session_id', sessionId)
          setStatus('success')
          // Redirect to dashboard after a short delay
          setTimeout(() => {
            navigate('/dashboard')
          }, 2000)
        } else {
          // If no session, something went wrong
          setStatus('error')
          setError('Failed to establish session')
        }
      } catch (err) {
        setStatus('error')
        setError('Authentication failed')
        console.error('Callback error:', err)
      }
    }

    handleCallback()
  }, [searchParams, navigate, updateUser])

  if (status === 'processing') {
    return (
      <div className="min-h-screen bg-spotify-black flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-spotify-green mx-auto mb-4"></div>
          <h2 className="text-2xl font-bold text-spotify-white mb-2">Connecting to Spotify</h2>
          <p className="text-spotify-gray">Please wait while we set up your account...</p>
        </div>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="min-h-screen bg-spotify-black flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="text-red-500 text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold text-spotify-white mb-4">Connection Failed</h2>
          <p className="text-spotify-gray mb-6">{error}</p>
          <button
            onClick={() => navigate('/')}
            className="btn-primary"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-spotify-black flex items-center justify-center">
      <div className="text-center">
        <div className="text-spotify-green text-6xl mb-4">✅</div>
        <h2 className="text-2xl font-bold text-spotify-white mb-2">Successfully Connected!</h2>
        <p className="text-spotify-gray mb-4">Redirecting to your dashboard...</p>
        <div className="animate-pulse text-spotify-green">●●●</div>
      </div>
    </div>
  )
}

export default CallbackPage
