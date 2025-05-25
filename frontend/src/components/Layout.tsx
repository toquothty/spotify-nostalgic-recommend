import React, { ReactNode } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { Music, BarChart3, User, LogOut, Menu, X, Sparkles } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { useState } from 'react'

interface LayoutProps {
  children: ReactNode
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { user, logout } = useAuth()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: Music },
    { name: 'Recommendations', href: '/recommendations', icon: Sparkles },
    { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  ]

  const handleLogout = () => {
    logout()
  }

  return (
    <div className="min-h-screen bg-spotify-black">
      {/* Mobile sidebar */}
      <div className={`fixed inset-0 z-50 lg:hidden ${sidebarOpen ? 'block' : 'hidden'}`}>
        <div className="fixed inset-0 bg-black/50" onClick={() => setSidebarOpen(false)} />
        <div className="fixed left-0 top-0 h-full w-64 bg-spotify-dark-gray">
          <div className="flex h-16 items-center justify-between px-4">
            <div className="flex items-center space-x-2">
              <Music className="h-8 w-8 text-spotify-green" />
              <span className="text-lg font-bold text-spotify-white">Nostalgic</span>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="text-spotify-gray hover:text-spotify-white"
            >
              <X className="h-6 w-6" />
            </button>
          </div>
          <nav className="mt-8 px-4">
            {navigation.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.href
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  onClick={() => setSidebarOpen(false)}
                  className={`flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-spotify-green text-spotify-black'
                      : 'text-spotify-gray hover:bg-spotify-gray/10 hover:text-spotify-white'
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  <span>{item.name}</span>
                </Link>
              )
            })}
          </nav>
        </div>
      </div>

      {/* Desktop sidebar */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col">
        <div className="flex flex-col bg-spotify-dark-gray">
          <div className="flex h-16 items-center px-4">
            <div className="flex items-center space-x-2">
              <Music className="h-8 w-8 text-spotify-green" />
              <span className="text-lg font-bold text-spotify-white">Nostalgic</span>
            </div>
          </div>
          <nav className="mt-8 flex-1 px-4">
            {navigation.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.href
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-spotify-green text-spotify-black'
                      : 'text-spotify-gray hover:bg-spotify-gray/10 hover:text-spotify-white'
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  <span>{item.name}</span>
                </Link>
              )
            })}
          </nav>
          
          {/* User section */}
          <div className="border-t border-spotify-gray/20 p-4">
            <div className="flex items-center space-x-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-spotify-green">
                <User className="h-4 w-4 text-spotify-black" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-spotify-white truncate">
                  {user?.display_name || 'User'}
                </p>
                <p className="text-xs text-spotify-gray truncate">
                  {user?.email}
                </p>
              </div>
              <button
                onClick={handleLogout}
                className="text-spotify-gray hover:text-spotify-white"
                title="Logout"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Mobile header */}
        <div className="flex h-16 items-center justify-between bg-spotify-dark-gray px-4 lg:hidden">
          <button
            onClick={() => setSidebarOpen(true)}
            className="text-spotify-gray hover:text-spotify-white"
          >
            <Menu className="h-6 w-6" />
          </button>
          <div className="flex items-center space-x-2">
            <Music className="h-6 w-6 text-spotify-green" />
            <span className="font-bold text-spotify-white">Nostalgic</span>
          </div>
          <button
            onClick={handleLogout}
            className="text-spotify-gray hover:text-spotify-white"
          >
            <LogOut className="h-5 w-5" />
          </button>
        </div>

        {/* Page content */}
        <main className="flex-1">
          {children}
        </main>
      </div>
    </div>
  )
}

export default Layout
