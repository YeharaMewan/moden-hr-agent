// frontend/components/chat/ChatContainer.js
'use client'

import { useState, useEffect, useRef } from 'react'
import { useAuth } from '@/context/AuthContext'
import { chatAPI, formatApiError } from '@/lib/api'
import ChatMessage from './ChatMessage'
import ChatInput from './ChatInput'
import TypingIndicator from './TypingIndicator'

export default function ChatContainer() {
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [sessionId, setSessionId] = useState(null)
  const messagesEndRef = useRef(null)
  const { user, isHR } = useAuth()

  // Generate session ID on mount
  useEffect(() => {
    const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    setSessionId(newSessionId)
    
    // Add welcome message
    addWelcomeMessage()
  }, [])

  // Scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const addWelcomeMessage = () => {
    const welcomeMessage = {
      id: 'welcome',
      type: 'assistant',
      content: getWelcomeMessage(),
      timestamp: new Date(),
      sender: 'HR AI Assistant'
    }
    setMessages([welcomeMessage])
  }

  const getWelcomeMessage = () => {
    const name = user?.full_name || user?.username || 'there'
    const baseMessage = `Hello ${name}! 👋 I'm your HR AI Assistant. How can I help you today?`
    
    if (isHR) {
      return `${baseMessage}

🏢 **As an HR user, you can:**
• Search and manage candidates: "Find Java developers"
• Review leave requests: "Show pending leaves"
• Calculate payroll: "Calculate IT department payroll"
• Manage employee information

💬 **You can ask me in English or Sinhala!**
🔍 Try: "මට java දන්නා candidates ලා ලබාදෙන්න"`
    } else {
      return `${baseMessage}

👤 **You can:**
• Request leave: "I need leave next week"
• Check leave status: "What's my leave balance?"
• View payroll: "Calculate my payroll"
• Get HR information

💬 **You can ask me in English or Sinhala!**
🏖️ Try: "මට leave request එකක් දැමීමට අවශයි"`
    }
  }

  const sendMessage = async (messageText, fileData = null) => {
    if (!messageText.trim() && !fileData) return

    setError(null)
    
    // Add user message
    const userMessage = {
      id: `user_${Date.now()}`,
      type: 'user',
      content: messageText,
      timestamp: new Date(),
      sender: user?.username || 'You',
      fileData
    }
    
    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)

    try {
      let response

      if (fileData) {
        // Handle file upload
        response = await chatAPI.uploadCV(fileData.file, {
          name: fileData.name,
          email: fileData.email,
          position: fileData.position,
          phone: fileData.phone
        })
      } else {
        // Regular chat message
        response = await chatAPI.sendMessage(messageText, sessionId)
      }

      // Add assistant response
      const assistantMessage = {
        id: `assistant_${Date.now()}`,
        type: 'assistant',
        content: response.data.response || 'I received your message.',
        timestamp: new Date(),
        sender: 'HR AI Assistant',
        agent: response.data.agent,
        intent: response.data.intent,
        requiresAction: response.data.requires_action,
        actionData: response.data.action_data
      }

      setMessages(prev => [...prev, assistantMessage])
      
    } catch (error) {
      console.error('Error sending message:', error)
      
      const errorMessage = {
        id: `error_${Date.now()}`,
        type: 'error',
        content: `Sorry, I encountered an error: ${formatApiError(error)}`,
        timestamp: new Date(),
        sender: 'System'
      }

      setMessages(prev => [...prev, errorMessage])
      setError(formatApiError(error))
      
    } finally {
      setIsLoading(false)
    }
  }

  const clearChat = () => {
    setMessages([])
    addWelcomeMessage()
    setError(null)
  }

  return (
    <div className="flex flex-col h-full bg-white">

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}
        
        {isLoading && <TypingIndicator />}
        
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
            <div className="flex">
              <svg className="h-5 w-5 text-red-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {error}
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Chat Input */}
      <div className="border-t border-gray-200 bg-white flex-shrink-0">
        <ChatInput onSendMessage={sendMessage} isLoading={isLoading} isHR={isHR} />
      </div>
    </div>
  )
}