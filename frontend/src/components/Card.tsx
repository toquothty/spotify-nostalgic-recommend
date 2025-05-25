import React, { ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
}

export const Card: React.FC<CardProps> = ({ children, className = '' }) => {
  return (
    <div className={`bg-spotify-dark-gray rounded-lg p-6 ${className}`}>
      {children}
    </div>
  )
}

interface CardHeaderProps {
  title: string
  subtitle?: string
  action?: ReactNode
}

export const CardHeader: React.FC<CardHeaderProps> = ({ title, subtitle, action }) => {
  return (
    <div className="flex items-center justify-between mb-4">
      <div>
        <h3 className="text-lg font-semibold text-spotify-white">{title}</h3>
        {subtitle && <p className="text-sm text-spotify-gray mt-1">{subtitle}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}

interface StatCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon?: ReactNode
  trend?: {
    value: number
    label: string
  }
}

export const StatCard: React.FC<StatCardProps> = ({ title, value, subtitle, icon, trend }) => {
  return (
    <Card>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-spotify-gray">{title}</p>
          <p className="text-2xl font-bold text-spotify-white mt-1">{value}</p>
          {subtitle && <p className="text-xs text-spotify-gray mt-1">{subtitle}</p>}
          {trend && (
            <div className="flex items-center mt-2">
              <span className={`text-xs ${trend.value > 0 ? 'text-green-400' : 'text-red-400'}`}>
                {trend.value > 0 ? '+' : ''}{trend.value}%
              </span>
              <span className="text-xs text-spotify-gray ml-1">{trend.label}</span>
            </div>
          )}
        </div>
        {icon && (
          <div className="text-spotify-green">
            {icon}
          </div>
        )}
      </div>
    </Card>
  )
}

interface ActionCardProps {
  title: string
  description: string
  buttonText: string
  onAction: () => void
  isLoading?: boolean
  disabled?: boolean
  icon?: ReactNode
}

export const ActionCard: React.FC<ActionCardProps> = ({
  title,
  description,
  buttonText,
  onAction,
  isLoading = false,
  disabled = false,
  icon
}) => {
  return (
    <Card>
      <div className="flex items-start space-x-4">
        {icon && (
          <div className="flex-shrink-0 text-spotify-green">
            {icon}
          </div>
        )}
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-spotify-white mb-2">{title}</h3>
          <p className="text-spotify-gray mb-4">{description}</p>
          <button
            onClick={onAction}
            disabled={disabled || isLoading}
            className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
                <span>Loading...</span>
              </div>
            ) : (
              buttonText
            )}
          </button>
        </div>
      </div>
    </Card>
  )
}
