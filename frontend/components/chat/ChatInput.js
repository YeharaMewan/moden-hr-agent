// frontend/components/chat/ChatInput.js
'use client'

import { useState, useRef } from 'react'

export default function ChatInput({ onSendMessage, isLoading, isHR }) {
  const [message, setMessage] = useState('')
  const [showFileUpload, setShowFileUpload] = useState(false)
  const [fileData, setFileData] = useState({
    file: null,
    name: '',
    email: '',
    position: '',
    phone: ''
  })
  const fileInputRef = useRef(null)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!message.trim() && !fileData.file) return

    if (fileData.file) {
      // Send file upload
      onSendMessage('CV file uploaded', fileData)
      setFileData({
        file: null,
        name: '',
        email: '',
        position: '',
        phone: ''
      })
      setShowFileUpload(false)
    } else {
      // Send regular message
      onSendMessage(message)
    }
    
    setMessage('')
  }

  const handleFileSelect = (e) => {
    const file = e.target.files[0]
    if (file) {
      // Validate file type
      const allowedTypes = ['text/plain', 'application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
      if (!allowedTypes.includes(file.type)) {
        alert('Please select a valid CV file (.txt, .pdf, .doc, .docx)')
        return
      }

      // Validate file size (10MB limit)
      if (file.size > 10 * 1024 * 1024) {
        alert('File size must be less than 10MB')
        return
      }

      setFileData(prev => ({ ...prev, file }))
      setShowFileUpload(true)
    }
  }

  const handleFileDataChange = (field, value) => {
    setFileData(prev => ({ ...prev, [field]: value }))
  }

  const cancelFileUpload = () => {
    setFileData({
      file: null,
      name: '',
      email: '',
      position: '',
      phone: ''
    })
    setShowFileUpload(false)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const suggestions = [
    "I need leave next week",
    "What's my leave balance?",
    "Calculate my payroll",
    isHR ? "Find Java developers" : "Check my leave status",
    isHR ? "Show pending leaves" : "Request sick leave",
    isHR ? "Calculate IT department payroll" : "Show my payroll history"
  ]

  return (
    <div className="p-4">
      {/* File Upload Modal */}
      {showFileUpload && fileData.file && (
        <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-blue-900">CV Upload Details</h3>
            <button
              onClick={cancelFileUpload}
              className="text-blue-600 hover:text-blue-800 transition-colors"
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          <div className="flex items-center space-x-2 mb-3">
            <svg className="h-5 w-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
            <span className="text-sm text-blue-900 font-medium">{fileData.file.name}</span>
            <span className="text-xs text-blue-600">({(fileData.file.size / 1024).toFixed(1)} KB)</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <input
              type="text"
              placeholder="Candidate Name"
              value={fileData.name}
              onChange={(e) => handleFileDataChange('name', e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <input
              type="email"
              placeholder="Email Address"
              value={fileData.email}
              onChange={(e) => handleFileDataChange('email', e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <input
              type="text"
              placeholder="Position Applied"
              value={fileData.position}
              onChange={(e) => handleFileDataChange('position', e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <input
              type="tel"
              placeholder="Phone Number"
              value={fileData.phone}
              onChange={(e) => handleFileDataChange('phone', e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>
      )}

      {/* Suggestions */}
      {message === '' && !showFileUpload && (
        <div className="mb-3">
          <div className="text-xs text-gray-500 mb-2">Quick suggestions:</div>
          <div className="flex flex-wrap gap-2">
            {suggestions.slice(0, 3).map((suggestion, index) => (
              <button
                key={index}
                onClick={() => setMessage(suggestion)}
                className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-full transition-colors"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="flex items-end space-x-3">
        <div className="flex-1">
          <div className="relative">
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Type your message... (English or Sinhala)"
              rows={1}
              className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              style={{ minHeight: '48px', maxHeight: '120px' }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSubmit(e)
                }
              }}
              disabled={isLoading}
            />
            
            {/* File Upload Button (HR only) */}
            {isHR && (
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="absolute right-2 top-2 p-2 text-gray-400 hover:text-gray-600 transition-colors"
                title="Upload CV"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                </svg>
              </button>
            )}
          </div>

          {/* Hidden File Input */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".txt,.pdf,.doc,.docx"
            onChange={handleFileSelect}
            className="hidden"
          />
        </div>

        {/* Send Button */}
        <button
          type="submit"
          disabled={isLoading || (!message.trim() && !fileData.file)}
          className={`px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors ${
            isLoading || (!message.trim() && !fileData.file) ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {isLoading ? (
            <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          ) : (
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          )}
        </button>
      </form>

      {/* Input Help Text */}
      <div className="mt-2 text-xs text-gray-500">
        Press Enter to send, Shift+Enter for new line
        {isHR && " • Click 📎 to upload CV files"}
      </div>
    </div>
  )
}