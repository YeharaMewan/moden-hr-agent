// frontend/components/layout/Layout.js
'use client'

import { useAuth } from '@/context/AuthContext'
import Header from './Header'

export default function Layout({ children }) {
  const { user, logout } = useAuth()

  return (
    <div className="h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <Header user={user} onLogout={logout} />
      
      {/* Main Content */}
      <main className="flex-1 overflow-hidden">
        {children}
      </main>
    </div>
  )
}