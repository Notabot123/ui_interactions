import { useState } from 'react'
import TreeExplorer from './components/TreeExplorer'
import ComponentViewer from './components/ComponentViewer'
import AIPanel from './components/AIPanel'
import { allComponents } from './data/components'
import { useTracker } from './hooks/useTracker'
import './styles.css'

export default function App() {
  const [selected, setSelected] = useState(allComponents.find(c => c.name.includes('Hydraulic Pump')) || allComponents[0])
  const tracker = useTracker()
  return <div className="appShell">
    <TreeExplorer selected={selected} onSelect={setSelected} track={tracker.track} />
    <ComponentViewer component={selected} track={tracker.track} />
    <AIPanel events={tracker.events} prediction={tracker.prediction} summarise={tracker.summarise} />
    <div className="heatmapLayer">{tracker.heatPoints.map(p => <span key={p.id} className="heatPoint" style={{ left: p.x, top: p.y }} />)}</div>
  </div>
}
