// frontend/components/chat/ChatMessage.js
'use client'

import { useState } from 'react'
import { format } from 'date-fns'

export default function ChatMessage({ message }) {
  const [showDetails, setShowDetails] = useState(false)

  const isUser = message.type === 'user'
  const isError = message.type === 'error'
  const isAssistant = message.type === 'assistant'

  const formatMessageContent = (content) => {
    if (!content) return ''

    // Convert markdown-style formatting to HTML-like structure
    return content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code>$1</code>')
      .replace(/###\s(.*$)/gim, '<h3>$1</h3>')
      .replace(/##\s(.*$)/gim, '<h2>$1</h2>')
      .replace(/•\s(.*$)/gim, '<li>$1</li>')
      .replace(/^\s*\n\n/gm, '<br>')
      .replace(/\n/g, '<br>')
  }

  const getMessageIcon = () => {
    if (isUser) {
      return (
        <div className="h-8 w-8 bg-blue-600 rounded-full flex items-center justify-center">
          <span className="text-white text-sm font-medium">
            {message.sender?.charAt(0).toUpperCase() || 'U'}
          </span>
        </div>
      )
    }

    if (isError) {
      return (
        <div className="h-8 w-8 bg-red-500 rounded-full flex items-center justify-center">
          <svg className="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
      )
    }

    // Assistant message
    return (
      <div className="h-8 w-8 bg-green-500 rounded-full flex items-center justify-center">
        <svg className="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z" />
        </svg>
      </div>
    )
  }

  const getAgentBadge = () => {
    if (!message.agent || message.agent === 'router') return null

    const agentNames = {
      'leave_agent': { name: 'Leave', color: 'bg-blue-100 text-blue-800' },
      'ats_agent': { name: 'ATS', color: 'bg-purple-100 text-purple-800' },
      'payroll_agent': { name: 'Payroll', color: 'bg-green-100 text-green-800' }
    }

    const agent = agentNames[message.agent]
    if (!agent) return null

    return (
      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${agent.color}`}>
        {agent.name}
      </span>
    )
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-fade-in`}>
      <div className={`flex max-w-xs lg:max-w-md xl:max-w-lg ${isUser ? 'flex-row-reverse' : 'flex-row'} items-start space-x-2`}>
        {/* Avatar */}
        <div className={`flex-shrink-0 ${isUser ? 'ml-2' : 'mr-2'}`}>
          {getMessageIcon()}
        </div>

        {/* Message Content */}
        <div className={`${isUser ? 'mr-2' : 'ml-2'}`}>
          {/* Message Header */}
          <div className={`flex items-center space-x-2 mb-1 ${isUser ? 'justify-end' : 'justify-start'}`}>
            <span className="text-xs text-gray-500 font-medium">
              {message.sender || (isUser ? 'You' : 'Assistant')}
            </span>
            {getAgentBadge()}
            <span className="text-xs text-gray-400">
              {format(new Date(message.timestamp), 'HH:mm')}
            </span>
          </div>

          {/* Message Bubble */}
          <div
            className={`rounded-lg px-4 py-2 ${
              isUser
                ? 'bg-blue-600 text-white'
                : isError
                ? 'bg-red-50 text-red-800 border border-red-200'
                : 'bg-gray-100 text-gray-900'
            }`}
          >
            {/* File Upload Info */}
            {message.fileData && (
              <div className="mb-2 p-2 bg-blue-50 border border-blue-200 rounded text-sm">
                <div className="flex items-center space-x-2">
                  <svg className="h-4 w-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                  <span className="text-blue-800 font-medium">{message.fileData.file.name}</span>
                </div>
              </div>
            )}

            {/* Message Text */}
            <div 
              className="prose prose-sm max-w-none"
              dangerouslySetInnerHTML={{ 
                __html: formatMessageContent(message.content) 
              }}
            />

            {/* Action Buttons for Assistant Messages */}
            {isAssistant && message.requiresAction && (
              <div className="mt-3 pt-2 border-t border-gray-200">
                <div className="text-xs text-gray-500 mb-2">
                  This message requires additional action
                </div>
                {message.actionData && (
                  <button
                    onClick={() => setShowDetails(!showDetails)}
                    className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded hover:bg-blue-200 transition-colors"
                  >
                    {showDetails ? 'Hide Details' : 'Show Details'}
                  </button>
                )}
              </div>
            )}

            {/* Details Panel */}
            {showDetails && message.actionData && (
              <div className="mt-2 p-2 bg-gray-50 border border-gray-200 rounded text-xs">
                <pre className="whitespace-pre-wrap text-gray-600">
                  {JSON.stringify(message.actionData, null, 2)}
                </pre>
              </div>
            )}
          </div>

          {/* Intent Badge */}
          {message.intent && message.intent !== 'general' && (
            <div className="mt-1 text-xs text-gray-400">
              Intent: {message.intent.replace('_', ' ')}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}