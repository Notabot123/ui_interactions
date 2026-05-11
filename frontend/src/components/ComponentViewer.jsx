import { Box, FileText, History, ScanLine } from 'lucide-react'
import { useState } from 'react'

export default function ComponentViewer({ component, track }) {
  const [tab, setTab] = useState('overview')
  const [priority, setPriority] = useState('Normal')
  if (!component) return <main className="viewer empty">Select a component to begin.</main>

  const action = (type, id, label, e, extra = {}) => track(type, id, { label, componentId: component.id, ...extra }, e)

  return <main className="viewer">
    <div className="heroCard">
      <div className="componentImage"><Box size={96}/><span>3D model placeholder</span></div>
      <div className="componentHeader">
        <div className="eyebrow">{component.group} subsystem</div>
        <h1>{component.name}</h1>
        <p>{component.description}</p>
        <div className="metrics">
          <span>Status <strong>{component.status}</strong></span>
          <span>Pressure <strong>{component.pressure}</strong></span>
          <span>Temperature <strong>{component.temperature}</strong></span>
          <span>Asset ID <strong>{component.code}</strong></span>
        </div>
        <div className="actions">
          <button id="btn-inspect" onMouseEnter={e => action('hover','btn-inspect','Inspect Component',e)} onClick={e => action('click','btn-inspect','Inspect Component',e)}><ScanLine size={16}/> Inspect</button>
          <button id="btn-open-diagram" onMouseEnter={e => action('hover','btn-open-diagram','Open Diagram',e)} onClick={e => action('click','btn-open-diagram','Open Diagram',e)}><FileText size={16}/> Open Diagram</button>
          <button id="btn-maintenance" onMouseEnter={e => action('hover','btn-maintenance','Maintenance History',e)} onClick={e => action('click','btn-maintenance','Maintenance History',e)}><History size={16}/> Maintenance History</button>
        </div>
      </div>
    </div>

    <div className="tabs">
      {['overview','specs','docs'].map(t => <button key={t} id={`tab-${t}`} className={tab === t ? 'selected' : ''}
        onClick={e => { setTab(t); action('click', `tab-${t}`, `Tab ${t}`, e) }}>{t}</button>)}
    </div>

    <section className="detailGrid">
      <div className="panel">
        <h3>{tab === 'overview' ? 'Operational overview' : tab === 'specs' ? 'Technical specifications' : 'Documentation'}</h3>
        <p>Representative content for a complex asset viewer. In the real system this area could show drawings, simulation data, 3D models, inspection workflows and linked documentation.</p>
        <ul>
          <li>Last inspection: 17 days ago</li>
          <li>Linked drawings: 4</li>
          <li>Open work orders: {component.status === 'Operational' ? 0 : 2}</li>
        </ul>
      </div>
      <div className="panel formPanel">
        <h3>Operator annotations</h3>
        <label>Notes<textarea id="input-notes" placeholder="Add observation..." onChange={e => action('input','input-notes','Notes field',e,{ value: e.target.value })}/></label>
        <label>Priority<select id="select-priority" value={priority} onChange={e => { setPriority(e.target.value); action('change','select-priority','Priority selector',e,{ value: e.target.value }) }}>
          <option>Low</option><option>Normal</option><option>High</option><option>Critical</option>
        </select></label>
      </div>
    </section>
  </main>
}
