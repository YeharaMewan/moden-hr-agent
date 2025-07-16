// frontend/app/layout.js
import './globals.css'
import { AuthProvider } from '@/context/AuthContext'

export const metadata = {
  title: 'HR AI Assistant',
  description: 'Intelligent HR Management System powered by AI',
  keywords: 'HR, AI, Assistant, Management, Leave, Payroll, ATS',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body className="font-sans antialiased">
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  )
}