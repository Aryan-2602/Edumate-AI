import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { AuthProvider } from '@/contexts/AuthContext'
import { QueryProvider } from '@/contexts/QueryContext'
import { Toaster } from 'react-hot-toast'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'EduMate-AI - AI-Powered Learning Platform',
  description: 'Transform your notes and textbooks into interactive learning experiences with AI-powered Q&A, quizzes, and flashcards.',
  keywords: 'AI, education, learning, Q&A, quizzes, flashcards, study tools',
  authors: [{ name: 'EduMate-AI Team' }],
  viewport: 'width=device-width, initial-scale=1',
  robots: 'index, follow',
  openGraph: {
    title: 'EduMate-AI - AI-Powered Learning Platform',
    description: 'Transform your notes and textbooks into interactive learning experiences with AI-powered Q&A, quizzes, and flashcards.',
    type: 'website',
    locale: 'en_US',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'EduMate-AI - AI-Powered Learning Platform',
    description: 'Transform your notes and textbooks into interactive learning experiences with AI-powered Q&A, quizzes, and flashcards.',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="h-full">
      <body className={`${inter.className} h-full bg-gray-50`}>
        <QueryProvider>
          <AuthProvider>
            {children}
            <Toaster
              position="top-right"
              toastOptions={{
                duration: 4000,
                style: {
                  background: '#363636',
                  color: '#fff',
                },
                success: {
                  duration: 3000,
                  iconTheme: {
                    primary: '#22c55e',
                    secondary: '#fff',
                  },
                },
                error: {
                  duration: 5000,
                  iconTheme: {
                    primary: '#ef4444',
                    secondary: '#fff',
                  },
                },
              }}
            />
          </AuthProvider>
        </QueryProvider>
      </body>
    </html>
  )
}
