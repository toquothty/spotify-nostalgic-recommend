import React, { Component, ErrorInfo, ReactNode } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error?: Error
  errorInfo?: ErrorInfo
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo)
    this.setState({ error, errorInfo })
  }

  handleReset = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="min-h-screen bg-spotify-black flex items-center justify-center p-4">
          <div className="max-w-md w-full text-center">
            <div className="bg-spotify-dark-gray rounded-lg p-8">
              <div className="flex justify-center mb-4">
                <div className="bg-red-500/20 rounded-full p-4">
                  <AlertTriangle className="h-12 w-12 text-red-400" />
                </div>
              </div>
              
              <h2 className="text-2xl font-bold text-spotify-white mb-4">
                Something went wrong
              </h2>
              
              <p className="text-spotify-gray mb-6">
                We encountered an unexpected error. Please try refreshing the page or contact support if the problem persists.
              </p>

              {this.state.error && (
                <div className="bg-red-900/20 border border-red-500/20 rounded-lg p-4 mb-6 text-left">
                  <h3 className="text-sm font-medium text-red-400 mb-2">Error Details:</h3>
                  <pre className="text-xs text-red-300 overflow-auto">
                    {this.state.error.message}
                  </pre>
                </div>
              )}

              <div className="space-y-3">
                <button
                  onClick={this.handleReset}
                  className="w-full btn-primary flex items-center justify-center space-x-2"
                >
                  <RefreshCw className="h-4 w-4" />
                  <span>Try Again</span>
                </button>
                
                <button
                  onClick={() => window.location.reload()}
                  className="w-full bg-spotify-gray/20 hover:bg-spotify-gray/30 text-spotify-white py-2 px-4 rounded-lg transition-colors"
                >
                  Refresh Page
                </button>
              </div>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
