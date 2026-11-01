'use client'

import { useEffect, useRef, useState } from 'react'

const RECONNECT_MIN_MS = 500
const RECONNECT_MAX_MS = 5000

// A live game's feed. A lost connection comes back by itself, and the snapshot of the new
// connection fills in everything that was missed. `clockOffset` is server time minus browser time.
export default function useLiveSocket<T extends object>(url: string, onMessage: (message: T) => void) {
  const [connected, setConnected] = useState(false)
  const clockOffset = useRef<number | null>(null)

  useEffect(() => {
    let socket: WebSocket
    let retry: ReturnType<typeof setTimeout>
    let delay = RECONNECT_MIN_MS
    let stopped = false

    function connect() {
      socket = new WebSocket(url)

      socket.onopen = () => {
        delay = RECONNECT_MIN_MS
        clockOffset.current = null
        setConnected(true)
      }

      socket.onmessage = ({ data }) => {
        const message: T = JSON.parse(data)
        if ('server_time' in message) {
          // A message arrives late, never early, so the largest offset is the closest to the truth.
          const offset = Date.parse(message.server_time as string) - Date.now()
          clockOffset.current = Math.max(clockOffset.current ?? offset, offset)
        }
        onMessage(message)
      }

      socket.onclose = () => {
        setConnected(false)
        if (stopped) return
        retry = setTimeout(connect, delay)
        delay = Math.min(delay * 2, RECONNECT_MAX_MS)
      }
    }

    connect()

    return () => {
      stopped = true
      clearTimeout(retry)
      socket.close()
    }
  }, [url, onMessage])

  return { connected, clockOffset }
}
