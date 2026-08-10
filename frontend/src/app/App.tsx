import { useEffect, useState } from 'react'

import { ChartRenderer } from '../components/ChartRenderer'
import {
  advanceReplay,
  getReplay,
  pauseReplay,
  resetReplay,
  resumeReplay,
  startReplay,
} from '../services/api'
import type { ReplayState } from '../types/replay'

const DISPLAY_TICK_MS = 800

export function App() {
  const [replay, setReplay] = useState<ReplayState | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    getReplay()
      .then(setReplay)
      .catch(() => setError('Replay API unavailable'))
  }, [])

  useEffect(() => {
    if (!replay || replay.status !== 'running' || busy) return

    const timer = window.setTimeout(() => {
      advanceReplay(60)
        .then((state) => {
          setReplay(state)
          setError(null)
        })
        .catch(() => setError('Replay advance failed'))
    }, DISPLAY_TICK_MS)

    return () => window.clearTimeout(timer)
  }, [replay, busy])

  async function runControl(action: () => Promise<ReplayState>) {
    setBusy(true)
    try {
      const state = await action()
      setReplay(state)
      setError(null)
    } catch {
      setError('Replay control failed')
    } finally {
      setBusy(false)
    }
  }

  if (!replay) {
    return (
      <main className="shell">
        <section className="replay-panel">
          <p className="eyebrow">CHARTVISION CORE</p>
          <h1>Replay MVP</h1>
          <p>{error ?? 'Loading controlled replay…'}</p>
        </section>
      </main>
    )
  }

  const progress = `${replay.position}/${replay.total}`
  const replayTime = replay.current_time
    ? new Date(replay.current_time).toLocaleString()
    : 'Not started'

  return (
    <main className="shell">
      <section className="replay-panel">
        <header className="replay-header">
          <div>
            <p className="eyebrow">CHARTVISION CORE</p>
            <h1>Replay MVP</h1>
          </div>
          <div className={`status status--${replay.status}`}>{replay.status}</div>
        </header>

        <div className="metadata" aria-label="Replay metadata">
          <span>{replay.asset}</span>
          <span>{replay.timeframe}</span>
          <span>Candles {progress}</span>
          <span>{replayTime}</span>
        </div>

        <ChartRenderer candles={replay.candles} />

        <div className="controls" aria-label="Replay controls">
          <button
            type="button"
            onClick={() => runControl(startReplay)}
            disabled={busy || replay.status !== 'idle'}
          >
            Start
          </button>
          <button
            type="button"
            onClick={() => runControl(pauseReplay)}
            disabled={busy || replay.status !== 'running'}
          >
            Pause
          </button>
          <button
            type="button"
            onClick={() => runControl(resumeReplay)}
            disabled={busy || replay.status !== 'paused'}
          >
            Resume
          </button>
          <button type="button" onClick={() => runControl(resetReplay)} disabled={busy}>
            Reset
          </button>
        </div>

        {error && <p className="error">{error}</p>}

        <p className="attribution">
          Charting library by{' '}
          <a href="https://www.tradingview.com/" target="_blank" rel="noreferrer">
            TradingView
          </a>
        </p>
      </section>
    </main>
  )
}
