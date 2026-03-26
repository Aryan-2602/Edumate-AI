import type { User as FirebaseUser } from 'firebase/auth'

export type ApiError = Error & { status?: number; body?: unknown }

function getApiBaseUrl(): string {
  const base = process.env.NEXT_PUBLIC_API_URL
  if (!base) {
    throw new Error(
      'NEXT_PUBLIC_API_URL is not set (e.g. http://127.0.0.1:8000).'
    )
  }
  return base.replace(/\/+$/, '')
}

async function readErrorBody(res: Response): Promise<unknown> {
  const contentType = res.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    try {
      return await res.json()
    } catch {
      return null
    }
  }
  try {
    return await res.text()
  } catch {
    return null
  }
}

function toApiError(message: string, status?: number, body?: unknown): ApiError {
  const err = new Error(message) as ApiError
  err.status = status
  err.body = body
  return err
}

export async function getIdToken(user: FirebaseUser): Promise<string> {
  return await user.getIdToken()
}

async function apiFetch(
  path: string,
  init: RequestInit & { token: string }
): Promise<Response> {
  const url = `${getApiBaseUrl()}${path.startsWith('/') ? '' : '/'}${path}`
  const headers = new Headers(init.headers || {})
  headers.set('Authorization', `Bearer ${init.token}`)

  return await fetch(url, {
    ...init,
    headers,
  })
}

async function apiJson<T>(
  path: string,
  init: Omit<RequestInit, 'body'> & { token: string; body?: unknown }
): Promise<T> {
  const headers = new Headers(init.headers || {})
  headers.set('Accept', 'application/json')

  const res = await apiFetch(path, {
    ...init,
    headers,
    body: init.body === undefined ? undefined : JSON.stringify(init.body),
  })

  if (!res.ok) {
    const body = await readErrorBody(res)
    const detail =
      typeof body === 'object' && body && 'detail' in body
        ? // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (body as any).detail
        : undefined
    throw toApiError(
      detail ? String(detail) : `Request failed: ${res.status} ${res.statusText}`,
      res.status,
      body
    )
  }

  return (await res.json()) as T
}

export type UploadAcceptedResponse = {
  message: string
  document_id: number
  title: string
  processing_status: 'pending' | 'processing' | 'completed' | 'failed' | string
  chunk_count: number
  file_size: number
}

export async function uploadDocument(args: {
  token: string
  file: File
  title: string
}): Promise<UploadAcceptedResponse> {
  const form = new FormData()
  form.set('file', args.file)
  form.set('title', args.title)

  const res = await apiFetch('/api/v1/documents/upload', {
    method: 'POST',
    token: args.token,
    body: form,
  })

  if (res.status !== 202) {
    const body = await readErrorBody(res)
    throw toApiError(
      `Upload failed: ${res.status} ${res.statusText}`,
      res.status,
      body
    )
  }

  return (await res.json()) as UploadAcceptedResponse
}

export type DocumentStatusResponse = {
  id: number
  title: string
  processing_status?: 'pending' | 'processing' | 'completed' | 'failed' | string
  processing_error?: string | null
  is_processed?: boolean
  chunk_count?: number
  file_name?: string
}

export async function getDocument(args: {
  token: string
  documentId: number
}): Promise<DocumentStatusResponse> {
  return await apiJson<DocumentStatusResponse>(
    `/api/v1/documents/${args.documentId}`,
    {
      method: 'GET',
      token: args.token,
      headers: { 'Content-Type': 'application/json' },
    }
  )
}

export type AskResponse = {
  question_id: number
  question: string
  answer: string
  sources: unknown[]
  confidence_score: number | null
}

export async function askQuestion(args: {
  token: string
  question: string
  document_ids?: number[]
  top_k?: number
}): Promise<AskResponse> {
  return await apiJson<AskResponse>('/api/v1/ai/ask', {
    method: 'POST',
    token: args.token,
    headers: { 'Content-Type': 'application/json' },
    body: {
      question: args.question,
      document_ids: args.document_ids,
      top_k: args.top_k,
    },
  })
}

export type GenerateQuizResponse = {
  quiz_id: number
  title: string
  description: string | null
  question_count: number
  questions: unknown[]
}

export async function generateQuiz(args: {
  token: string
  document_id: number
  num_questions?: number
}): Promise<GenerateQuizResponse> {
  return await apiJson<GenerateQuizResponse>('/api/v1/ai/generate-quiz', {
    method: 'POST',
    token: args.token,
    headers: { 'Content-Type': 'application/json' },
    body: {
      document_id: args.document_id,
      num_questions: args.num_questions,
    },
  })
}

export type GenerateFlashcardsResponse = {
  flashcard_set_id: number
  document_id: number
  flashcards: unknown[]
  total_cards: number
}

export async function generateFlashcards(args: {
  token: string
  document_id: number
  num_cards?: number
}): Promise<GenerateFlashcardsResponse> {
  return await apiJson<GenerateFlashcardsResponse>('/api/v1/ai/generate-flashcards', {
    method: 'POST',
    token: args.token,
    headers: { 'Content-Type': 'application/json' },
    body: {
      document_id: args.document_id,
      num_cards: args.num_cards,
    },
  })
}

