const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export async function getHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_URL}/health`)
  if (!response.ok) throw new Error('Backend unavailable')
  return response.json()
}
