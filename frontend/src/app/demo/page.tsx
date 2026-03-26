'use client'

import React, { useMemo, useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import {
  askQuestion,
  generateFlashcards,
  generateQuiz,
  getDocument,
  getIdToken,
  uploadDocument,
  type ApiError,
} from '@/lib/api'

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function formatError(err: unknown): string {
  if (!err) return 'Unknown error'
  if (err instanceof Error) {
    const apiErr = err as ApiError
    if (apiErr.status) {
      const bodyStr =
        apiErr.body === undefined ? '' : `\n\nBody:\n${JSON.stringify(apiErr.body, null, 2)}`
      return `${apiErr.message}\n\nStatus: ${apiErr.status}${bodyStr}`
    }
    return err.message
  }
  try {
    return JSON.stringify(err, null, 2)
  } catch {
    return String(err)
  }
}

export default function DemoPage() {
  const { user, loading, signInWithGoogle, signOut } = useAuth()

  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState<string>('Demo upload')
  const [uploadResult, setUploadResult] = useState<unknown>(null)

  const [documentId, setDocumentId] = useState<number | null>(null)
  const [documentStatus, setDocumentStatus] = useState<unknown>(null)

  const [question, setQuestion] = useState<string>('What are the key points?')
  const [askResult, setAskResult] = useState<unknown>(null)

  const [quizCount, setQuizCount] = useState<number | ''>('')
  const [quizResult, setQuizResult] = useState<unknown>(null)

  const [flashcardCount, setFlashcardCount] = useState<number | ''>('')
  const [flashcardsResult, setFlashcardsResult] = useState<unknown>(null)

  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const canCallDocBasedEndpoints = useMemo(() => {
    return typeof documentId === 'number' && documentId > 0
  }, [documentId])

  async function withToken<T>(fn: (token: string) => Promise<T>): Promise<T> {
    if (!user) throw new Error('Not signed in.')
    const token = await getIdToken(user)
    return await fn(token)
  }

  async function handleUpload() {
    setError(null)
    setUploadResult(null)
    setDocumentStatus(null)
    setDocumentId(null)
    setAskResult(null)
    setQuizResult(null)
    setFlashcardsResult(null)

    if (!file) {
      setError('Pick a file first.')
      return
    }

    setBusy('Uploading…')
    try {
      const res = await withToken((token) =>
        uploadDocument({ token, file, title: title.trim() || 'Untitled' })
      )
      setUploadResult(res)
      setDocumentId(res.document_id)
    } catch (e) {
      setError(formatError(e))
    } finally {
      setBusy(null)
    }
  }

  async function handleRefreshStatus() {
    if (!canCallDocBasedEndpoints || !documentId) return
    setError(null)
    setBusy('Fetching document status…')
    try {
      const res = await withToken((token) =>
        getDocument({ token, documentId })
      )
      setDocumentStatus(res)
      return res
    } catch (e) {
      setError(formatError(e))
    } finally {
      setBusy(null)
    }
  }

  async function handlePollUntilCompleted() {
    if (!canCallDocBasedEndpoints || !documentId) return
    setError(null)
    setBusy('Polling until processed…')
    try {
      for (let i = 0; i < 60; i++) {
        const res = await withToken((token) =>
          getDocument({ token, documentId })
        )
        setDocumentStatus(res)
        const status = (res.processing_status || '').toString()
        if (status === 'completed') return
        if (status === 'failed') {
          throw new Error(res.processing_error || 'Document processing failed.')
        }
        await sleep(1000)
      }
      throw new Error('Timed out waiting for document processing.')
    } catch (e) {
      setError(formatError(e))
    } finally {
      setBusy(null)
    }
  }

  async function handleAsk() {
    setError(null)
    setAskResult(null)
    setBusy('Asking…')
    try {
      const res = await withToken((token) =>
        askQuestion({
          token,
          question: question.trim(),
          document_ids: documentId ? [documentId] : undefined,
        })
      )
      setAskResult(res)
    } catch (e) {
      setError(formatError(e))
    } finally {
      setBusy(null)
    }
  }

  async function handleGenerateQuiz() {
    if (!documentId) return
    setError(null)
    setQuizResult(null)
    setBusy('Generating quiz…')
    try {
      const res = await withToken((token) =>
        generateQuiz({
          token,
          document_id: documentId,
          num_questions: quizCount === '' ? undefined : quizCount,
        })
      )
      setQuizResult(res)
    } catch (e) {
      setError(formatError(e))
    } finally {
      setBusy(null)
    }
  }

  async function handleGenerateFlashcards() {
    if (!documentId) return
    setError(null)
    setFlashcardsResult(null)
    setBusy('Generating flashcards…')
    try {
      const res = await withToken((token) =>
        generateFlashcards({
          token,
          document_id: documentId,
          num_cards: flashcardCount === '' ? undefined : flashcardCount,
        })
      )
      setFlashcardsResult(res)
    } catch (e) {
      setError(formatError(e))
    } finally {
      setBusy(null)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen p-6">
        <div className="max-w-3xl mx-auto">Loading…</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen p-6">
      <div className="max-w-3xl mx-auto space-y-8">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">
              Minimal backend workflow demo
            </h1>
            <p className="text-sm text-gray-600">
              Upload → poll processing → ask → quiz → flashcards
            </p>
          </div>

          <div className="flex items-center gap-3">
            {user ? (
              <>
                <div className="text-right">
                  <div className="text-sm font-medium text-gray-900">
                    {user.displayName || user.email || user.uid}
                  </div>
                  <div className="text-xs text-gray-600">Signed in</div>
                </div>
                <button
                  className="btn-outline"
                  onClick={() => void signOut()}
                >
                  Sign out
                </button>
              </>
            ) : (
              <button
                className="btn-primary"
                onClick={() => void signInWithGoogle()}
              >
                Sign in with Google
              </button>
            )}
          </div>
        </div>

        {!user ? (
          <div className="rounded-xl bg-white p-5 shadow-soft">
            <p className="text-gray-700">
              Sign in to call the backend (Firebase ID token is attached as a
              bearer token).
            </p>
          </div>
        ) : (
          <>
            <section className="rounded-xl bg-white p-5 shadow-soft space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">Upload</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <input
                  className="md:col-span-2 block w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                  placeholder="Title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  disabled={!!busy}
                />
                <button className="btn-primary" onClick={() => void handleUpload()} disabled={!!busy}>
                  Upload
                </button>
              </div>
              <input
                type="file"
                className="block w-full text-sm"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                disabled={!!busy}
              />
              {documentId ? (
                <div className="text-sm text-gray-700">
                  Document ID: <span className="font-mono">{documentId}</span>
                </div>
              ) : null}
              {uploadResult ? (
                <pre className="text-xs bg-gray-50 border border-gray-200 rounded-lg p-3 overflow-auto">
                  {JSON.stringify(uploadResult, null, 2)}
                </pre>
              ) : null}
            </section>

            <section className="rounded-xl bg-white p-5 shadow-soft space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">
                Document processing status
              </h2>
              <div className="flex flex-wrap gap-3">
                <button
                  className="btn-outline"
                  onClick={() => void handleRefreshStatus()}
                  disabled={!!busy || !canCallDocBasedEndpoints}
                >
                  Refresh
                </button>
                <button
                  className="btn-primary"
                  onClick={() => void handlePollUntilCompleted()}
                  disabled={!!busy || !canCallDocBasedEndpoints}
                >
                  Poll until completed
                </button>
              </div>
              {documentStatus ? (
                <pre className="text-xs bg-gray-50 border border-gray-200 rounded-lg p-3 overflow-auto">
                  {JSON.stringify(documentStatus, null, 2)}
                </pre>
              ) : (
                <div className="text-sm text-gray-600">
                  Upload a document first.
                </div>
              )}
            </section>

            <section className="rounded-xl bg-white p-5 shadow-soft space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">Ask (RAG)</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <input
                  className="md:col-span-2 block w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                  placeholder="Question"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  disabled={!!busy}
                />
                <button className="btn-primary" onClick={() => void handleAsk()} disabled={!!busy}>
                  Ask
                </button>
              </div>
              {askResult ? (
                <pre className="text-xs bg-gray-50 border border-gray-200 rounded-lg p-3 overflow-auto">
                  {JSON.stringify(askResult, null, 2)}
                </pre>
              ) : null}
            </section>

            <section className="rounded-xl bg-white p-5 shadow-soft space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">
                Generate quiz
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <input
                  className="md:col-span-2 block w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                  placeholder="Number of questions (optional)"
                  inputMode="numeric"
                  value={quizCount}
                  onChange={(e) => {
                    const v = e.target.value.trim()
                    setQuizCount(v === '' ? '' : Number(v))
                  }}
                  disabled={!!busy || !canCallDocBasedEndpoints}
                />
                <button
                  className="btn-primary"
                  onClick={() => void handleGenerateQuiz()}
                  disabled={!!busy || !canCallDocBasedEndpoints}
                >
                  Generate
                </button>
              </div>
              {quizResult ? (
                <pre className="text-xs bg-gray-50 border border-gray-200 rounded-lg p-3 overflow-auto">
                  {JSON.stringify(quizResult, null, 2)}
                </pre>
              ) : null}
            </section>

            <section className="rounded-xl bg-white p-5 shadow-soft space-y-4">
              <h2 className="text-lg font-semibold text-gray-900">
                Generate flashcards
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <input
                  className="md:col-span-2 block w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                  placeholder="Number of cards (optional)"
                  inputMode="numeric"
                  value={flashcardCount}
                  onChange={(e) => {
                    const v = e.target.value.trim()
                    setFlashcardCount(v === '' ? '' : Number(v))
                  }}
                  disabled={!!busy || !canCallDocBasedEndpoints}
                />
                <button
                  className="btn-primary"
                  onClick={() => void handleGenerateFlashcards()}
                  disabled={!!busy || !canCallDocBasedEndpoints}
                >
                  Generate
                </button>
              </div>
              {flashcardsResult ? (
                <pre className="text-xs bg-gray-50 border border-gray-200 rounded-lg p-3 overflow-auto">
                  {JSON.stringify(flashcardsResult, null, 2)}
                </pre>
              ) : null}
            </section>
          </>
        )}

        {busy ? (
          <div className="text-sm text-gray-700">Working: {busy}</div>
        ) : null}
        {error ? (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900 whitespace-pre-wrap">
            {error}
          </div>
        ) : null}
      </div>
    </div>
  )
}

