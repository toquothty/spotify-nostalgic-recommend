import React, { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { authApi } from '../services/api'
import { Calendar, ArrowRight, Sparkles } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

const OnboardingPage: React.FC = () => {
  const { sessionId, updateUser } = useAuth()
  const navigate = useNavigate()
  const [dateOfBirth, setDateOfBirth] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!dateOfBirth) {
      setError('Please enter your date of birth')
      return
    }

    if (!sessionId) {
      setError('Session not found. Please log in again.')
      return
    }

    // Validate age (must be at least 13 for Spotify)
    const birthDate = new Date(dateOfBirth)
    const today = new Date()
    let age = today.getFullYear() - birthDate.getFullYear()
    const monthDiff = today.getMonth() - birthDate.getMonth()
    
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
      age--
    }

    if (age < 13) {
      setError('You must be at least 13 years old to use this service')
      return
    }

    if (age > 120) {
      setError('Please enter a valid date of birth')
      return
    }

    try {
      setIsLoading(true)
      setError('')
      
      await authApi.completeOnboarding(sessionId, dateOfBirth)
      
      // Update user context to reflect onboarding completion
      updateUser({ needs_onboarding: false, date_of_birth: dateOfBirth })
      
      // Redirect to dashboard
      navigate('/dashboard')
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to complete onboarding'
      setError(typeof errorMessage === 'string' ? errorMessage : 'Failed to complete onboarding')
    } finally {
      setIsLoading(false)
    }
  }

  const calculateFormativeYears = () => {
    if (!dateOfBirth) return null
    
    const birthDate = new Date(dateOfBirth)
    const startYear = birthDate.getFullYear() + 12
    const endYear = birthDate.getFullYear() + 18
    
    return { startYear, endYear }
  }

  const formativeYears = calculateFormativeYears()

  return (
    <div className="min-h-screen bg-gradient-to-br from-spotify-black via-gray-900 to-spotify-black flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <div className="bg-spotify-green/20 rounded-full p-4">
              <Sparkles className="h-12 w-12 text-spotify-green" />
            </div>
          </div>
          <h1 className="text-3xl font-bold text-spotify-white mb-2">
            Welcome to Nostalgic Recommender!
          </h1>
          <p className="text-spotify-gray">
            To unlock nostalgic recommendations from your formative years, we need to know when you were born.
          </p>
        </div>

        <div className="card">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="dateOfBirth" className="block text-sm font-medium text-spotify-white mb-2">
                Date of Birth
              </label>
              <div className="relative">
                <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-spotify-gray" />
                <input
                  type="date"
                  id="dateOfBirth"
                  value={dateOfBirth}
                  onChange={(e) => setDateOfBirth(e.target.value)}
                  max={new Date().toISOString().split('T')[0]}
                  min="1900-01-01"
                  className="w-full pl-10 pr-4 py-3 bg-spotify-black border border-spotify-gray/30 rounded-lg text-spotify-white placeholder-spotify-gray focus:outline-none focus:border-spotify-green transition-colors"
                  required
                />
              </div>
            </div>

            {formativeYears && (
              <div className="bg-spotify-green/10 border border-spotify-green/20 rounded-lg p-4">
                <h3 className="text-sm font-medium text-spotify-green mb-2">
                  Your Formative Years
                </h3>
                <p className="text-sm text-spotify-gray">
                  We'll find nostalgic hits from {formativeYears.startYear} - {formativeYears.endYear} 
                  (when you were 12-18 years old) that match your current music taste.
                </p>
              </div>
            )}

            {error && (
              <div className="bg-red-900/20 border border-red-500/20 rounded-lg p-4">
                <p className="text-red-400 text-sm">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading || !dateOfBirth}
              className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
            >
              {isLoading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
                  <span>Setting up your profile...</span>
                </>
              ) : (
                <>
                  <span>Complete Setup</span>
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-spotify-gray/20">
            <div className="text-center">
              <h3 className="text-sm font-medium text-spotify-white mb-2">
                Why do we need this?
              </h3>
              <ul className="text-xs text-spotify-gray space-y-1">
                <li>• Find nostalgic hits from your formative years (ages 12-18)</li>
                <li>• Analyze how your music taste evolved over time</li>
                <li>• Generate age-appropriate recommendations</li>
                <li>• Your data is private and secure</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default OnboardingPage
