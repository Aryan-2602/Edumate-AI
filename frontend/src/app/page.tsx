'use client'

import React from 'react'
import Link from 'next/link'
import { useAuth } from '@/contexts/AuthContext'
import { 
  AcademicCapIcon, 
  ChatBubbleLeftRightIcon, 
  DocumentTextIcon, 
  LightBulbIcon,
  SparklesIcon,
  BookOpenIcon,
  ChartBarIcon,
  UserGroupIcon
} from '@heroicons/react/24/outline'
import { motion } from 'framer-motion'

export default function HomePage() {
  const { user, signInWithGoogle } = useAuth()

  const features = [
    {
      icon: DocumentTextIcon,
      title: 'Smart Document Processing',
      description: 'Upload PDFs, Word documents, and text files. Our AI automatically chunks and processes your content for optimal learning.',
    },
    {
      icon: ChatBubbleLeftRightIcon,
      title: 'AI-Powered Q&A',
      description: 'Ask questions about your study materials and get instant, accurate answers using our advanced RAG system.',
    },
    {
      icon: LightBulbIcon,
      title: 'Interactive Quizzes',
      description: 'Generate personalized quizzes from your documents to test your understanding and retention.',
    },
    {
      icon: AcademicCapIcon,
      title: 'Smart Flashcards',
      description: 'Create effective flashcards automatically from your study materials for efficient memorization.',
    },
    {
      icon: ChartBarIcon,
      title: 'Progress Tracking',
      description: 'Monitor your learning progress with detailed analytics and insights about your study patterns.',
    },
    {
      icon: UserGroupIcon,
      title: 'Collaborative Learning',
      description: 'Share study materials and collaborate with classmates in a secure, AI-enhanced environment.',
    },
  ]

  const handleGetStarted = () => {
    if (user) {
      // User is already logged in, redirect to dashboard
      window.location.href = '/dashboard'
    } else {
      // User needs to sign in
      signInWithGoogle()
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Navigation */}
      <nav className="relative z-10 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <SparklesIcon className="h-8 w-8 text-primary-600" />
            <span className="text-2xl font-bold gradient-text">EduMate-AI</span>
          </div>
          
          <div className="hidden md:flex items-center space-x-8">
            <Link href="#features" className="text-gray-600 hover:text-primary-600 transition-colors">
              Features
            </Link>
            <Link href="#how-it-works" className="text-gray-600 hover:text-primary-600 transition-colors">
              How It Works
            </Link>
            <Link href="#pricing" className="text-gray-600 hover:text-primary-600 transition-colors">
              Pricing
            </Link>
          </div>

          <div className="flex items-center space-x-4">
            {user ? (
              <Link href="/dashboard" className="btn-primary">
                Go to Dashboard
              </Link>
            ) : (
              <>
                <button onClick={signInWithGoogle} className="btn-outline">
                  Sign In
                </button>
                <button onClick={handleGetStarted} className="btn-primary">
                  Get Started
                </button>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative px-6 py-20 lg:py-32">
        <div className="max-w-7xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <h1 className="text-5xl md:text-7xl font-bold text-gray-900 mb-6">
              Transform Your
              <span className="gradient-text block">Learning Experience</span>
            </h1>
            
            <p className="text-xl md:text-2xl text-gray-600 mb-8 max-w-3xl mx-auto">
              Upload your notes and textbooks, and let AI create interactive learning experiences with Q&A, quizzes, and flashcards.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button onClick={handleGetStarted} className="btn-primary text-lg px-8 py-4">
                Start Learning with AI
              </button>
              <Link href="#how-it-works" className="btn-outline text-lg px-8 py-4">
                See How It Works
              </Link>
            </div>
          </motion.div>

          {/* Hero Visual */}
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="mt-16 relative"
          >
            <div className="relative max-w-4xl mx-auto">
              <div className="absolute inset-0 bg-gradient-to-r from-primary-400 to-accent-400 rounded-3xl blur-3xl opacity-20"></div>
              <div className="relative bg-white rounded-3xl p-8 shadow-strong">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="space-y-4">
                    <div className="bg-primary-50 rounded-xl p-4">
                      <DocumentTextIcon className="h-8 w-8 text-primary-600 mb-2" />
                      <h3 className="font-semibold text-gray-900">Upload Documents</h3>
                      <p className="text-sm text-gray-600">PDFs, Word docs, text files</p>
                    </div>
                    <div className="bg-accent-50 rounded-xl p-4">
                      <ChatBubbleLeftRightIcon className="h-8 w-8 text-accent-600 mb-2" />
                      <h3 className="font-semibold text-gray-900">Ask Questions</h3>
                      <p className="text-sm text-gray-600">Get AI-powered answers</p>
                    </div>
                  </div>
                  
                  <div className="space-y-4">
                    <div className="bg-success-50 rounded-xl p-4">
                      <LightBulbIcon className="h-8 w-8 text-success-600 mb-2" />
                      <h3 className="font-semibold text-gray-900">Generate Quizzes</h3>
                      <p className="text-sm text-gray-600">Test your knowledge</p>
                    </div>
                    <div className="bg-warning-50 rounded-xl p-4">
                      <AcademicCapIcon className="h-8 w-8 text-warning-600 mb-2" />
                      <h3 className="font-semibold text-gray-900">Create Flashcards</h3>
                      <p className="text-sm text-gray-600">Memorize key concepts</p>
                    </div>
                  </div>
                  
                  <div className="space-y-4">
                    <div className="bg-secondary-50 rounded-xl p-4">
                      <ChartBarIcon className="h-8 w-8 text-secondary-600 mb-2" />
                      <h3 className="font-semibold text-gray-900">Track Progress</h3>
                      <p className="text-sm text-gray-600">Monitor your learning</p>
                    </div>
                    <div className="bg-purple-50 rounded-xl p-4">
                      <UserGroupIcon className="h-8 w-8 text-purple-600 mb-2" />
                      <h3 className="font-semibold text-gray-900">Collaborate</h3>
                      <p className="text-sm text-gray-600">Study with others</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="px-6 py-20 bg-white">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
              Powerful Features for Modern Learning
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Our AI-powered platform combines cutting-edge technology with proven learning methodologies to create an unparalleled educational experience.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: index * 0.1 }}
                viewport={{ once: true }}
                className="card-hover"
              >
                <feature.icon className="h-12 w-12 text-primary-600 mb-4" />
                <h3 className="text-xl font-semibold text-gray-900 mb-3">
                  {feature.title}
                </h3>
                <p className="text-gray-600 leading-relaxed">
                  {feature.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="px-6 py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
              How It Works
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Get started in minutes with our simple three-step process
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                step: '01',
                title: 'Upload Your Materials',
                description: 'Upload PDFs, Word documents, or text files. Our AI will process and analyze your content.',
                icon: DocumentTextIcon,
              },
              {
                step: '02',
                title: 'AI Processing & Embedding',
                description: 'We use advanced NLP to chunk your documents and create semantic embeddings for intelligent search.',
                icon: SparklesIcon,
              },
              {
                step: '03',
                title: 'Interactive Learning',
                description: 'Ask questions, generate quizzes, create flashcards, and track your progress with AI assistance.',
                icon: AcademicCapIcon,
              },
            ].map((item, index) => (
              <motion.div
                key={item.step}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: index * 0.2 }}
                viewport={{ once: true }}
                className="text-center"
              >
                <div className="relative mb-6">
                  <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto">
                    <span className="text-2xl font-bold text-primary-600">{item.step}</span>
                  </div>
                  <item.icon className="h-8 w-8 text-primary-600 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-3">
                  {item.title}
                </h3>
                <p className="text-gray-600 leading-relaxed">
                  {item.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="px-6 py-20 bg-gradient-to-r from-primary-600 to-accent-600">
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
          >
            <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
              Ready to Transform Your Learning?
            </h2>
            <p className="text-xl text-primary-100 mb-8">
              Join thousands of students who are already using AI to enhance their study experience.
            </p>
            <button onClick={handleGetStarted} className="btn bg-white text-primary-600 hover:bg-gray-100 text-lg px-8 py-4">
              Start Learning Today
            </button>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white px-6 py-12">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center space-x-2 mb-4">
                <SparklesIcon className="h-8 w-8 text-primary-400" />
                <span className="text-2xl font-bold">EduMate-AI</span>
              </div>
              <p className="text-gray-400">
                AI-powered educational platform for interactive learning experiences.
              </p>
            </div>
            
            <div>
              <h3 className="font-semibold mb-4">Product</h3>
              <ul className="space-y-2 text-gray-400">
                <li><Link href="#features" className="hover:text-white transition-colors">Features</Link></li>
                <li><Link href="#pricing" className="hover:text-white transition-colors">Pricing</Link></li>
                <li><Link href="/docs" className="hover:text-white transition-colors">Documentation</Link></li>
              </ul>
            </div>
            
            <div>
              <h3 className="font-semibold mb-4">Company</h3>
              <ul className="space-y-2 text-gray-400">
                <li><Link href="/about" className="hover:text-white transition-colors">About</Link></li>
                <li><Link href="/blog" className="hover:text-white transition-colors">Blog</Link></li>
                <li><Link href="/careers" className="hover:text-white transition-colors">Careers</Link></li>
              </ul>
            </div>
            
            <div>
              <h3 className="font-semibold mb-4">Support</h3>
              <ul className="space-y-2 text-gray-400">
                <li><Link href="/help" className="hover:text-white transition-colors">Help Center</Link></li>
                <li><Link href="/contact" className="hover:text-white transition-colors">Contact</Link></li>
                <li><Link href="/status" className="hover:text-white transition-colors">Status</Link></li>
              </ul>
            </div>
          </div>
          
          <div className="border-t border-gray-800 mt-8 pt-8 text-center text-gray-400">
            <p>&copy; 2024 EduMate-AI. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
