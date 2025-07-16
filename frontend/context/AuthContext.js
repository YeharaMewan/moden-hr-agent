// frontend/context/AuthContext.js
'use client'

import { createContext, useContext, useState, useEffect } from 'react'
import { authAPI } from '@/lib/api'
import Cookies from 'js-cookie'

const AuthContext = createContext()

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Check for existing token on mount
  useEffect(() => {
    checkAuthStatus()
  }, [])

  const checkAuthStatus = async () => {
    try {
      const token = Cookies.get('hr_token')
      if (!token) {
        setLoading(false)
        return
      }

      // Verify token with backend
      const response = await authAPI.getProfile()
      if (response.data.user) {
        setUser(response.data.user)
      } else {
        // Invalid token
        Cookies.remove('hr_token')
      }
    } catch (error) {
      console.error('Auth check failed:', error)
      Cookies.remove('hr_token')
    } finally {
      setLoading(false)
    }
  }

  const login = async (username, password) => {
    try {
      setError(null)
      setLoading(true)

      const response = await authAPI.login(username, password)
      
      if (response.data.token) {
        // Store token in cookie
        Cookies.set('hr_token', response.data.token, { 
          expires: 1, // 1 day
          secure: process.env.NODE_ENV === 'production',
          sameSite: 'strict'
        })

        setUser(response.data.user)
        return { success: true }
      } else {
        throw new Error('No token received')
      }
    } catch (error) {
      const errorMessage = error.response?.data?.error || 'Login failed'
      setError(errorMessage)
      return { success: false, error: errorMessage }
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    Cookies.remove('hr_token')
    setUser(null)
    setError(null)
  }

  const value = {
    user,
    loading,
    error,
    login,
    logout,
    isAuthenticated: !!user,
    isHR: user?.role === 'hr',
    isUser: user?.role === 'user'
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}