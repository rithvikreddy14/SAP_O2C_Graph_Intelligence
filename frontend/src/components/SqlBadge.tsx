import { useState } from 'react'
import { ChevronDown, ChevronUp, Code2 } from 'lucide-react'

interface Props {
  sql: string
  rowCount?: number
}

export default function SqlBadge({ sql, rowCount }: Props) {
  const [open, setOpen] = useState(false)
  return (
    <div className="sql-badge">
      <button className="sql-toggle" onClick={() => setOpen(o => !o)}>
        <Code2 size={11} />
        <span>SQL</span>
        {rowCount !== undefined && (
          <span className="row-count">{rowCount} rows</span>
        )}
        {open ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
      </button>
      {open && <pre className="sql-block">{sql}</pre>}
    </div>
  )
}