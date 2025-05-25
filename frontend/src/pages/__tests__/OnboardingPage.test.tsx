/**
 * @jest-environment jsdom
 */
import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import OnboardingPage from '../OnboardingPage'
import { AuthProvider } from '../../contexts/AuthContext'
import * as api from '../../services/api'

// Mock the API
jest.mock('../../services/api')
const mockApi = api as jest.Mocked<typeof api>

// Mock react-router-dom
const mockNavigate = jest.fn()
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}))

// Mock AuthContext
const mockUpdateUser = jest.fn()
const mockAuthContext = {
  user: null,
  sessionId: 'test-session-id',
  isLoading: false,
  login: jest.fn(),
  logout: jest.fn(),
  updateUser: mockUpdateUser,
}

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => mockAuthContext,
  AuthProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

// Test wrapper component
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <BrowserRouter>
      <AuthProvider>
        {children}
      </AuthProvider>
    </BrowserRouter>
  )
}

describe('OnboardingPage', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders onboarding form correctly', () => {
    render(
      <TestWrapper>
        <OnboardingPage />
      </TestWrapper>
    )

    expect(screen.getByText('Welcome to Nostalgic Recommender!')).toBeInTheDocument()
    expect(screen.getByLabelText('Date of Birth')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /complete setup/i })).toBeInTheDocument()
  })

  it('shows formative years when date is entered', () => {
    render(
      <TestWrapper>
        <OnboardingPage />
      </TestWrapper>
    )

    const dateInput = screen.getByLabelText('Date of Birth')
    fireEvent.change(dateInput, { target: { value: '1990-05-15' } })

    expect(screen.getByText('Your Formative Years')).toBeInTheDocument()
    expect(screen.getByText(/2002 - 2008/)).toBeInTheDocument()
  })

  it('validates age requirement (must be 13+)', async () => {
    render(
      <TestWrapper>
        <OnboardingPage />
      </TestWrapper>
    )

    const dateInput = screen.getByLabelText('Date of Birth')
    const submitButton = screen.getByRole('button', { name: /complete setup/i })

    // Enter a date that makes user under 13
    const tooYoungDate = new Date()
    tooYoungDate.setFullYear(tooYoungDate.getFullYear() - 10)
    fireEvent.change(dateInput, { 
      target: { value: tooYoungDate.toISOString().split('T')[0] } 
    })

    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText('You must be at least 13 years old to use this service')).toBeInTheDocument()
    })

    expect(mockApi.authApi.completeOnboarding).not.toHaveBeenCalled()
  })

  it('validates reasonable age (not over 120)', async () => {
    render(
      <TestWrapper>
        <OnboardingPage />
      </TestWrapper>
    )

    const dateInput = screen.getByLabelText('Date of Birth')
    const submitButton = screen.getByRole('button', { name: /complete setup/i })

    fireEvent.change(dateInput, { target: { value: '1800-01-01' } })
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText('Please enter a valid date of birth')).toBeInTheDocument()
    })

    expect(mockApi.authApi.completeOnboarding).not.toHaveBeenCalled()
  })

  it('submits form successfully with valid data', async () => {
    mockApi.authApi.completeOnboarding.mockResolvedValue({ message: 'Success' })

    render(
      <TestWrapper>
        <OnboardingPage />
      </TestWrapper>
    )

    const dateInput = screen.getByLabelText('Date of Birth')
    const submitButton = screen.getByRole('button', { name: /complete setup/i })

    fireEvent.change(dateInput, { target: { value: '1990-05-15' } })
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(mockApi.authApi.completeOnboarding).toHaveBeenCalledWith('test-session-id', '1990-05-15')
    })

    expect(mockUpdateUser).toHaveBeenCalledWith({
      needs_onboarding: false,
      date_of_birth: '1990-05-15'
    })

    expect(mockNavigate).toHaveBeenCalledWith('/dashboard')
  })

  it('handles API errors gracefully', async () => {
    const errorResponse = {
      response: {
        data: {
          detail: 'Invalid date format'
        }
      }
    }
    mockApi.authApi.completeOnboarding.mockRejectedValue(errorResponse)

    render(
      <TestWrapper>
        <OnboardingPage />
      </TestWrapper>
    )

    const dateInput = screen.getByLabelText('Date of Birth')
    const submitButton = screen.getByRole('button', { name: /complete setup/i })

    fireEvent.change(dateInput, { target: { value: '1990-05-15' } })
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText('Invalid date format')).toBeInTheDocument()
    })

    expect(mockNavigate).not.toHaveBeenCalled()
  })

  it('shows loading state during submission', async () => {
    // Mock a delayed response
    mockApi.authApi.completeOnboarding.mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve({ message: 'Success' }), 100))
    )

    render(
      <TestWrapper>
        <OnboardingPage />
      </TestWrapper>
    )

    const dateInput = screen.getByLabelText('Date of Birth')
    const submitButton = screen.getByRole('button', { name: /complete setup/i })

    fireEvent.change(dateInput, { target: { value: '1990-05-15' } })
    fireEvent.click(submitButton)

    // Check loading state
    expect(screen.getByText('Setting up your profile...')).toBeInTheDocument()
    expect(submitButton).toBeDisabled()

    // Wait for completion
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard')
    })
  })

  it('requires session ID', async () => {
    // Mock no session ID
    const noSessionContext = {
      ...mockAuthContext,
      sessionId: null,
    }

    jest.mocked(require('../../contexts/AuthContext').useAuth).mockReturnValue(noSessionContext)

    render(
      <TestWrapper>
        <OnboardingPage />
      </TestWrapper>
    )

    const dateInput = screen.getByLabelText('Date of Birth')
    const submitButton = screen.getByRole('button', { name: /complete setup/i })

    fireEvent.change(dateInput, { target: { value: '1990-05-15' } })
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText('Session not found. Please log in again.')).toBeInTheDocument()
    })

    expect(mockApi.authApi.completeOnboarding).not.toHaveBeenCalled()
  })
})
