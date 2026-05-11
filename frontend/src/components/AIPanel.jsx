import { Brain, Sparkles } from 'lucide-react'
import { useState } from 'react'

export default function AIPanel({ events, prediction, summarise }) {
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(false)
  async function runSummary() {
    setLoading(true)
    try { setSummary(await summarise()) } catch (e) { setSummary({ summary: e.message, model: 'error', event_count: events.length }) }
    setLoading(false)
  }
  return <aside className="aiPanel">
    <div className="card prediction">
      <div className="cardTitle"><Brain size={17}/> Live next-action prediction</div>
      <h2>{prediction.action}</h2>
      <div className="confidence"><span style={{ width: `${Math.round((prediction.confidence || 0) * 100)}%` }} /></div>
      <p>{Math.round((prediction.confidence || 0) * 100)}% confidence · {prediction.reason}</p>
    </div>
    <div className="card">
      <div className="cardTitle">Live interaction feed</div>
      <div className="feed">
        {events.length === 0 && <p className="muted">No events yet.</p>}
        {events.slice(0, 16).map((e, i) => <div className="feedItem" key={`${e.timestamp}-${i}`}><b>{e.event_type}</b><span>{e.element_label}</span></div>)}
      </div>
    </div>
    <div className="card summaryCard">
      <button className="summaryButton" onClick={runSummary} disabled={loading}><Sparkles size={16}/>{loading ? 'Analysing...' : 'Generate UX Insights'}</button>
      {summary && <div className="summary"><div className="tinyTitle">{summary.model} · {summary.event_count} events</div><pre>{summary.summary}</pre></div>}
    </div>
  </aside>
}
