import { ChevronDown, ChevronRight, Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import { allComponents, componentTree } from '../data/components'

function score(item, query) {
  if (!query) return 0
  const q = query.toLowerCase()
  const text = `${item.name} ${item.code} ${item.group}`.toLowerCase()
  if (text.includes(q)) return 100 - text.indexOf(q)
  return q.split('').filter(ch => text.includes(ch)).length
}

export default function TreeExplorer({ selected, onSelect, track }) {
  const [open, setOpen] = useState(() => new Set(['Hydraulics']))
  const [query, setQuery] = useState('')
  const results = useMemo(() => allComponents.map(c => ({ ...c, _score: score(c, query) })).filter(c => c._score > 0).sort((a,b) => b._score - a._score).slice(0,5), [query])

  function toggle(group, e) {
    track('click', `tree-group-${group}`, { label: `Expand ${group}` }, e)
    setOpen(prev => {
      const next = new Set(prev)
      next.has(group) ? next.delete(group) : next.add(group)
      return next
    })
  }

  return <aside className="sidebar">
    <div className="brand">Interaction Intelligence <span>POC</span></div>
    <label className="searchBox">
      <Search size={16} />
      <input id="tree-search" placeholder="Search 120+ components..." value={query}
        onChange={e => { setQuery(e.target.value); track('input', 'tree-search', { label: 'Component search', value: e.target.value }) }} />
    </label>
    {query && <div className="searchResults">
      <div className="tinyTitle">Top matches</div>
      {results.map(r => <button key={r.id} onClick={e => { track('click', `search-result-${r.id}`, { label: `Search result ${r.name}`, componentId: r.id }, e); onSelect(r) }}>
        <strong>{r.name}</strong><span>{r.group} · {r.code}</span>
      </button>)}
    </div>}
    <div className="tree">
      {componentTree.map(group => <div key={group.group}>
        <button className="group" onClick={e => toggle(group.group, e)}>{open.has(group.group) ? <ChevronDown size={16}/> : <ChevronRight size={16}/>} {group.group}</button>
        {open.has(group.group) && <div className="items">
          {group.items.map(item => <button key={item.id} className={selected?.id === item.id ? 'active item' : 'item'}
            onMouseEnter={e => track('hover', `tree-item-${item.id}`, { label: item.name, componentId: item.id }, e)}
            onClick={e => { track('click', `tree-item-${item.id}`, { label: item.name, componentId: item.id }, e); onSelect(item) }}>
            <span>{item.name}</span><small>{item.code}</small>
          </button>)}
        </div>}
      </div>)}
    </div>
  </aside>
}
