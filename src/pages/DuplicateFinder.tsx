import { useState } from 'react'
import Layout from '../components/Layout'
import UploadZone from '../components/UploadZone'
import { IconSearch, IconDownload, IconCheck, IconX, IconInfo } from '../components/Icons'
import { downloadCSV } from '../utils'

type DupType = 'email' | 'company' | 'fullname'
type Status = 'processing' | 'success' | 'error'

interface Result {
  duplicate_count: number
  rows: Record<string, unknown>[]
}

const DUP_OPTIONS: { value: DupType; label: string; desc: string }[] = [
  { value: 'email',    label: 'Email Address',  desc: 'Find rows sharing the same email' },
  { value: 'company',  label: 'Company Name',   desc: 'Find rows from the same company' },
  { value: 'fullname', label: 'Full Name',       desc: 'Find rows with matching first + last name' },
]

const FILENAMES: Record<DupType, string> = {
  email:    'duplicate_emails.csv',
  company:  'common_company.csv',
  fullname: 'common_fullname.csv',
}

export default function DuplicateFinder() {
  const [files, setFiles]     = useState<File[]>([])
  const [dupType, setDupType] = useState<DupType>('email')
  const [status, setStatus]   = useState<{ type: Status; msg: string } | null>(null)
  const [result, setResult]   = useState<Result | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleProcess() {
    if (!files.length) {
      setStatus({ type: 'error', msg: 'Please select at least one CSV file.' })
      return
    }

    setLoading(true)
    setStatus({ type: 'processing', msg: 'Scanning for duplicates…' })
    setResult(null)

    const form = new FormData()
    files.forEach(f => form.append('files', f))
    form.append('duplicate_type', dupType)

    try {
      const res = await fetch('/api/duplicate-email-finder', { method: 'POST', body: form })
      let data: any
      try { data = await res.json() } catch { throw new Error(`Server error (HTTP ${res.status}) — the file may be unreadable or the server is temporarily unavailable.`) }

      if (!res.ok || data.error) {
        setStatus({ type: 'error', msg: data?.error || `Server error (HTTP ${res.status}).` })
      } else if (data.duplicate_count === 0) {
        setStatus({ type: 'success', msg: 'Scan complete — no duplicates found across your files.' })
      } else {
        setResult(data)
        setStatus({ type: 'success', msg: `Scan complete.` })
      }
    } catch (e: any) {
      setStatus({ type: 'error', msg: e?.message || 'Request failed. Check your connection and try again.' })
    } finally {
      setLoading(false)
    }
  }

  const headers = result?.rows[0] ? Object.keys(result.rows[0]) : []

  return (
    <Layout
      title="Duplicate Email Finder"
      description="Scan one or more CSV files to find duplicate contacts by email, company, or name."
    >
      {/* How it works */}
      <div className="card">
        <p className="card-title">How It Works</p>
        <div className="info-strip">
          <IconInfo />
          <p>
            Upload your CSV files and choose what to deduplicate on. The tool groups all rows that
            share the same value, shows a count, and exports a clean report.
            <br /><br />
            Recommended columns: <strong>email</strong>, <strong>first_name</strong>,{' '}
            <strong>last_name</strong>, <strong>company</strong>.
          </p>
        </div>
      </div>

      {/* Upload & config */}
      <div className="card">
        <p className="card-title">Configure &amp; Upload</p>

        {/* Duplicate type selector */}
        <div style={{ marginBottom: 20 }}>
          <div className="field-row" style={{ marginBottom: 12 }}>
            <span className="field-label">Detect duplicates by</span>
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {DUP_OPTIONS.map(opt => (
              <button
                key={opt.value}
                className="btn"
                style={{
                  background: dupType === opt.value ? 'var(--green-600)' : 'var(--surface)',
                  color: dupType === opt.value ? '#fff' : 'var(--text-muted)',
                  border: `1px solid ${dupType === opt.value ? 'var(--green-600)' : 'var(--border-strong)'}`,
                  boxShadow: dupType === opt.value ? 'var(--shadow-green)' : 'none',
                  flexDirection: 'column',
                  height: 'auto',
                  padding: '10px 18px',
                  gap: 2,
                  alignItems: 'flex-start',
                }}
                onClick={() => { setDupType(opt.value); setResult(null); setStatus(null) }}
              >
                <span style={{ fontWeight: 800, fontSize: '0.875rem' }}>{opt.label}</span>
                <span style={{ fontWeight: 500, fontSize: '0.75rem', opacity: 0.75 }}>{opt.desc}</span>
              </button>
            ))}
          </div>
        </div>

        <UploadZone
          multiple
          label="Drop your CSV files here"
          onFiles={fs => { setFiles(fs); setResult(null); setStatus(null) }}
        />

        <div className="btn-group">
          <button
            className="btn btn-primary btn-lg"
            onClick={handleProcess}
            disabled={loading || !files.length}
          >
            {loading
              ? <><span className="spinner" />Scanning…</>
              : <><IconSearch style={{ width: 18, height: 18 }} />Find Duplicates</>}
          </button>
        </div>

        {status && (
          <div className={`alert alert-${status.type === 'processing' ? 'loading' : status.type === 'success' ? 'success' : 'error'}`}>
            {status.type === 'processing' && <span className="spinner spinner-muted" />}
            {status.type === 'success'    && <IconCheck />}
            {status.type === 'error'      && <IconX />}
            {status.msg}
          </div>
        )}
      </div>

      {/* Results */}
      {result && result.duplicate_count > 0 && (
        <div className="card">
          <p className="card-title">Duplicates Found</p>

          <div className="result-banner">
            <div className="result-banner-count">
              <div className="result-banner-number">{result.duplicate_count.toLocaleString()}</div>
              <div className="result-banner-label">
                Duplicate group{result.duplicate_count !== 1 ? 's' : ''} detected
              </div>
            </div>
            <button
              className="btn"
              style={{ background: 'rgba(255,255,255,0.12)', border: '1px solid rgba(255,255,255,0.2)', color: '#fff' }}
              onClick={() => downloadCSV(FILENAMES[dupType], result.rows)}
            >
              <IconDownload />
              Download Report
            </button>
          </div>

          {/* Results table */}
          <div className="result-table-wrap">
            <table className="result-table">
              <thead>
                <tr>
                  {headers.map(h => <th key={h}>{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {result.rows.slice(0, 25).map((row, i) => (
                  <tr key={i}>
                    {headers.map(h => (
                      <td key={h}>
                        {h === 'Count'
                          ? <span className="badge">{String(row[h])}</span>
                          : String(row[h] ?? '')}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="table-footer">
              {result.duplicate_count > 25
                ? `Showing 25 of ${result.duplicate_count.toLocaleString()} groups — download CSV for full list`
                : `${result.duplicate_count} group${result.duplicate_count !== 1 ? 's' : ''} total`}
            </div>
          </div>

          <div className="btn-group">
            <button
              className="btn btn-primary"
              onClick={() => downloadCSV(FILENAMES[dupType], result.rows)}
            >
              <IconDownload />
              Download {FILENAMES[dupType]}
            </button>
          </div>
        </div>
      )}
    </Layout>
  )
}

