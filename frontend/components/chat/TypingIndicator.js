// frontend/components/chat/TypingIndicator.js
'use client'

export default function TypingIndicator() {
  return (
    <div className="flex justify-start animate-fade-in">
      <div className="flex items-start space-x-2 max-w-xs lg:max-w-md xl:max-w-lg">
        {/* AI Avatar */}
        <div className="flex-shrink-0 mr-2">
          <div className="h-8 w-8 bg-green-500 rounded-full flex items-center justify-center">
            <svg className="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z" />
            </svg>
          </div>
        </div>

        {/* Typing Bubble */}
        <div className="ml-2">
          <div className="flex items-center space-x-2 mb-1">
            <span className="text-xs text-gray-500 font-medium">HR AI Assistant</span>
            <span className="text-xs text-gray-400">typing...</span>
          </div>
          
          <div className="bg-gray-100 rounded-lg px-4 py-3">
            <div className="flex items-center space-x-1">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
              <span className="text-sm text-gray-500 ml-2">AI is thinking...</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}