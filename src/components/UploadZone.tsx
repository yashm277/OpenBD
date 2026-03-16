import { useRef, useState } from 'react'
import { IconUpload, IconCheck } from './Icons'

interface UploadZoneProps {
  multiple?: boolean
  label?: string
  description?: string
  accept?: string
  onFiles: (files: File[]) => void
}

export default function UploadZone({
  multiple = false,
  label = 'Drop files here or click to browse',
  description,
  accept = '.csv,.xlsx',
  onFiles,
}: UploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [selected, setSelected] = useState<File[]>([])
  const [dragging, setDragging] = useState(false)

  function handleList(list: FileList | null) {
    if (!list?.length) return
    const arr = Array.from(list)
    setSelected(arr)
    onFiles(arr)
  }

  return (
    <div
      className={`upload-zone${dragging ? ' dragging' : ''}`}
      role="button"
      tabIndex={0}
      onClick={() => inputRef.current?.click()}
      onKeyDown={e => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); inputRef.current?.click() }
      }}
      onDragOver={e => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={e => { e.preventDefault(); setDragging(false); handleList(e.dataTransfer.files) }}
    >
      <input
        ref={inputRef}
        type="file"
        multiple={multiple}
        accept={accept}
        style={{ display: 'none' }}
        onChange={e => handleList(e.target.files)}
      />

      <div className="upload-zone-icon">
        <IconUpload />
      </div>

      <div className="upload-zone-title">{label}</div>
      <div className="upload-zone-sub">
        {description ?? (
          <>Accepts <kbd>.csv</kbd> and <kbd>.xlsx</kbd></>
        )}
      </div>

      {selected.length > 0 && (
        <div className="file-chips">
          {selected.map(f => (
            <span key={`${f.name}-${f.size}`} className="file-chip">
              <IconCheck />
              <span>{f.name}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

