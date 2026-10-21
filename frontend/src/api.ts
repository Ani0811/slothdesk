import type {
  HealthResponse,
  FilesInventoryResponse,
  PlanResponse,
  ExecutionResponse,
  ExecutionManifest,
  UndoResponse,
} from './types'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errMsg = `Request failed (${res.status} ${res.statusText})`
    try {
      const data = await res.json()
      if (data && data.detail) {
        errMsg = data.detail
      }
    } catch {
      // Fallback to text or generic message
    }
    throw new Error(errMsg)
  }
  return res.json()
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`)
  return handleResponse<HealthResponse>(res)
}

export async function fetchFiles(): Promise<FilesInventoryResponse> {
  const res = await fetch(`${API_BASE}/files`)
  return handleResponse<FilesInventoryResponse>(res)
}

export async function createPlan(): Promise<PlanResponse> {
  const res = await fetch(`${API_BASE}/plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  return handleResponse<PlanResponse>(res)
}

export async function getPlan(planId: string): Promise<PlanResponse> {
  const res = await fetch(`${API_BASE}/plan/${encodeURIComponent(planId)}`)
  return handleResponse<PlanResponse>(res)
}

export async function executePlan(planId: string): Promise<ExecutionResponse> {
  const res = await fetch(`${API_BASE}/execute/${encodeURIComponent(planId)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  return handleResponse<ExecutionResponse>(res)
}

export async function fetchUndoHistory(): Promise<ExecutionManifest[]> {
  const res = await fetch(`${API_BASE}/undo`)
  return handleResponse<ExecutionManifest[]>(res)
}

export async function undoManifest(manifestId: string): Promise<UndoResponse> {
  const res = await fetch(`${API_BASE}/undo/${encodeURIComponent(manifestId)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  return handleResponse<UndoResponse>(res)
}
