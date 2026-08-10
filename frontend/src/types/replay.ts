export type ReplayStatus = 'idle' | 'running' | 'paused' | 'stopped' | 'finished'

export interface ReplayCandle {
  open_time: string
  close_time: string
  open: string
  high: string
  low: string
  close: string
}

export interface ReplayState {
  status: ReplayStatus
  asset: string
  timeframe: string
  position: number
  total: number
  current_time: string | null
  candles: ReplayCandle[]
}
