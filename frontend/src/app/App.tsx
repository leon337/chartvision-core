import { useEffect, useState } from 'react'
import { getHealth } from '../services/api'

export function App() {
  const [status, setStatus] = useState('checking')

  useEffect(() => {
    getHealth()
      .then(() => setStatus('ok'))
      .catch(() => setStatus('error'))
  }, [])

  return (
    <main className="shell">
      <section className="card">
        <p className="eyebrow">CHARTVISION CORE</p>
        <h1>Foundation</h1>
        <p>Estrutura inicial pronta para as fases de replay, visão e análise.</p>
        <div className={`status status--${status}`}>
          Backend: {status}
        </div>
      </section>
    </main>
  )
}
