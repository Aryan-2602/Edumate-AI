'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'
import { 
  User as FirebaseUser, 
  signInWithPopup, 
  GoogleAuthProvider, 
  signOut as firebaseSignOut,
  onAuthStateChanged,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword
} from 'firebase/auth'
import { getFirebaseAuth } from '@/lib/firebase'
import { useRouter } from 'next/navigation'

interface AuthContextType {
  user: FirebaseUser | null
  loading: boolean
  signInWithGoogle: () => Promise<void>
  signInWithEmail: (email: string, password: string) => Promise<void>
  signUpWithEmail: (email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<FirebaseUser | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  useEffect(() => {
    const auth = getFirebaseAuth()
    if (!auth) {
      setUser(null)
      setLoading(false)
      return
    }

    const unsubscribe = onAuthStateChanged(auth, (user) => {
      setUser(user)
      setLoading(false)
    })

    return unsubscribe
  }, [])

  const signInWithGoogle = async () => {
    try {
      const auth = getFirebaseAuth()
      if (!auth) {
        throw new Error('Firebase is not configured. Set NEXT_PUBLIC_FIREBASE_* env vars.')
      }
      const provider = new GoogleAuthProvider()
      provider.addScope('email')
      provider.addScope('profile')
      
      const result = await signInWithPopup(auth, provider)
      setUser(result.user)
      
      router.push('/demo')
    } catch (error) {
      console.error('Error signing in with Google:', error)
      throw error
    }
  }

  const signInWithEmail = async (email: string, password: string) => {
    try {
      const auth = getFirebaseAuth()
      if (!auth) {
        throw new Error('Firebase is not configured. Set NEXT_PUBLIC_FIREBASE_* env vars.')
      }
      const result = await signInWithEmailAndPassword(auth, email, password)
      setUser(result.user)
      
      router.push('/demo')
    } catch (error) {
      console.error('Error signing in with email:', error)
      throw error
    }
  }

  const signUpWithEmail = async (email: string, password: string) => {
    try {
      const auth = getFirebaseAuth()
      if (!auth) {
        throw new Error('Firebase is not configured. Set NEXT_PUBLIC_FIREBASE_* env vars.')
      }
      const result = await createUserWithEmailAndPassword(auth, email, password)
      setUser(result.user)
      
      router.push('/demo')
    } catch (error) {
      console.error('Error signing up with email:', error)
      throw error
    }
  }

  const signOut = async () => {
    try {
      const auth = getFirebaseAuth()
      if (auth) {
        await firebaseSignOut(auth)
      }
      setUser(null)
      
      // Redirect to home page after logout
      router.push('/')
    } catch (error) {
      console.error('Error signing out:', error)
      throw error
    }
  }

  const value: AuthContextType = {
    user,
    loading,
    signInWithGoogle,
    signInWithEmail,
    signUpWithEmail,
    signOut,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}
