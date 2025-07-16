// frontend/app/chat/page.js
'use client'

import ProtectedRoute from '@/components/auth/ProtectedRoute'
import Layout from '@/components/layout/Layout'
import ChatContainer from '@/components/chat/ChatContainer'

export default function ChatPage() {
  return (
    <ProtectedRoute>
      <Layout>
        <div className="h-full">
          <ChatContainer />
        </div>
      </Layout>
    </ProtectedRoute>
  )
}