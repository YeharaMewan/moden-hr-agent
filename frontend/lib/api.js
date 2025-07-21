// frontend/lib/api.js
import axios from 'axios'
import Cookies from 'js-cookie'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = Cookies.get('hr_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      Cookies.remove('hr_token')
      // Only redirect if we're in the browser
      if (typeof window !== 'undefined') {
        window.location.href = '/auth/login'
      }
    }
    return Promise.reject(error)
  }
)

// Authentication API
export const authAPI = {
  login: (username, password) =>
    api.post('/auth/login', { username, password }),
  
  getProfile: () =>
    api.get('/auth/profile'),
  
  logout: () => {
    Cookies.remove('hr_token')
    return Promise.resolve()
  }
}

// Chat API
export const chatAPI = {
  sendMessage: (message, sessionId = null) =>
    api.post('/chat/message', { 
      message, 
      session_id: sessionId || generateSessionId() 
    }),
  
  getChatHistory: (page = 1, limit = 20) =>
    api.get(`/chat/history?page=${page}&limit=${limit}`),
  
  getSessions: () =>
    api.get('/chat/sessions'),
  
  clearHistory: (sessionId = null) =>
    api.delete(`/chat/clear${sessionId ? `?session_id=${sessionId}` : ''}`),
  
  submitFeedback: (conversationId, feedback) =>
    api.post('/chat/feedback', { conversation_id: conversationId, ...feedback }),
  
  getChatStatus: () =>
    api.get('/chat/status')
}

// File Upload API
export const fileAPI = {
  uploadCV: (file, candidateData) => {
    const formData = new FormData()
    formData.append('cv_file', file)
    
    // Add candidate data to form
    Object.keys(candidateData).forEach(key => {
      if (candidateData[key]) {
        formData.append(key, candidateData[key])
      }
    })

    return api.post('/upload/cv', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  }
}

// Utility functions
export const generateSessionId = () => {
  return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

export const formatApiError = (error) => {
  if (error.response?.data?.error) {
    return error.response.data.error
  } else if (error.response?.data?.message) {
    return error.response.data.message
  } else if (error.message) {
    return error.message
  } else {
    return 'An unexpected error occurred'
  }
}

// Health check
export const healthCheck = () => api.get('/health')

export default api