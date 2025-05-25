import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { User } from '../types'
import { authApi } from '../services/api'

interface AuthContextType {
  user: User | null
  sessionId: string | null
  isLoading: boolean
  login: () => void
  logout: () => void
  updateUser: (userData: Partial<User>) => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

interface AuthProviderProps {
  children: ReactNode
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Check for session ID in URL params (from OAuth callback)
    const urlParams = new URLSearchParams(window.location.search)
    const sessionFromUrl = urlParams.get('session')
    
    if (sessionFromUrl) {
      setSessionId(sessionFromUrl)
      // Remove session from URL
      window.history.replaceState({}, document.title, window.location.pathname)
    } else {
      // Check localStorage for existing session
      const storedSession = localStorage.getItem('spotify_session_id')
      if (storedSession) {
        setSessionId(storedSession)
      }
    }
  }, [])

  useEffect(() => {
    if (sessionId) {
      // Store session in localStorage
      localStorage.setItem('spotify_session_id', sessionId)
      
      // Fetch user data
      fetchUserData()
    } else {
      setIsLoading(false)
    }
  }, [sessionId])

  const fetchUserData = async () => {
    if (!sessionId) return

    try {
      setIsLoading(true)
      const userData = await authApi.getCurrentUser(sessionId)
      setUser(userData)
    } catch (error) {
      console.error('Failed to fetch user data:', error)
      // Clear invalid session
      logout()
    } finally {
      setIsLoading(false)
    }
  }

  const login = async () => {
    try {
      const authData = await authApi.initiateLogin()
      window.location.href = authData.auth_url
    } catch (error) {
      console.error('Login failed:', error)
    }
  }

  const logout = () => {
    setUser(null)
    setSessionId(null)
    localStorage.removeItem('spotify_session_id')
    
    // Optionally call logout endpoint
    if (sessionId) {
      authApi.logout(sessionId).catch(console.error)
    }
  }

  const updateUser = (userData: Partial<User>) => {
    if (user) {
      setUser({ ...user, ...userData })
    }
  }

  const value: AuthContextType = {
    user,
    sessionId,
    isLoading,
    login,
    logout,
    updateUser,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}
