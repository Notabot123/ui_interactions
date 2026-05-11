import { useMemo, useState } from 'react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function useTracker() {
  const sessionId = useMemo(() => `session-${Date.now()}-${Math.random().toString(16).slice(2)}`, [])
  const [events, setEvents] = useState([])
  const [prediction, setPrediction] = useState({ action: 'Start interacting with the app', confidence: 0, reason: 'Waiting for telemetry.' })
  const [heatPoints, setHeatPoints] = useState([])

  async function track(eventType, elementId, details = {}, nativeEvent = null) {
    const payload = {
      session_id: sessionId,
      timestamp: Date.now(),
      event_type: eventType,
      element_id: elementId,
      element_label: details.label || elementId,
      page: details.page || 'component-workspace',
      component_id: details.componentId || null,
      x: nativeEvent?.clientX || null,
      y: nativeEvent?.clientY || null,
      value: details.value || null,
      metadata: details.metadata || {}
    }
    setEvents(prev => [payload, ...prev].slice(0, 80))
    if (payload.x && payload.y) {
      const point = { id: `${payload.timestamp}-${Math.random()}`, x: payload.x, y: payload.y }
      setHeatPoints(prev => [point, ...prev].slice(0, 30))
      setTimeout(() => setHeatPoints(prev => prev.filter(p => p.id !== point.id)), 2600)
    }
    try {
      const res = await fetch(`${API}/events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      if (res.ok) setPrediction(await res.json())
    } catch {
      setPrediction({ action: 'Backend unavailable', confidence: 0, reason: 'Start FastAPI on port 8000.' })
    }
  }

  async function summarise() {
    const res = await fetch(`${API}/summarise`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId })
    })
    if (!res.ok) throw new Error('No events available to summarise yet')
    return res.json()
  }

  return { sessionId, events, prediction, heatPoints, track, summarise }
}
