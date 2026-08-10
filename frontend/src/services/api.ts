import type { ReplayState } from '../types/replay'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init)
  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}`)
  }
  return response.json() as Promise<T>
}

export async function getHealth(): Promise<{ status: string }> {
  return requestJson('/health')
}

export async function getReplay(): Promise<ReplayState> {
  return requestJson('/replay')
}

export async function startReplay(): Promise<ReplayState> {
  return requestJson('/replay/start', { method: 'POST' })
}

export async function pauseReplay(): Promise<ReplayState> {
  return requestJson('/replay/pause', { method: 'POST' })
}

export async function resumeReplay(): Promise<ReplayState> {
  return requestJson('/replay/resume', { method: 'POST' })
}

export async function resetReplay(): Promise<ReplayState> {
  return requestJson('/replay/reset', { method: 'POST' })
}

export async function advanceReplay(seconds = 60): Promise<ReplayState> {
  const params = new URLSearchParams({ seconds: String(seconds) })
  return requestJson(`/replay/advance?${params.toString()}`, { method: 'POST' })
}
