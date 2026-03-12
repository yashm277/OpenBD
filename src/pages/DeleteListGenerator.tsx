import { useState } from 'react'
import Layout from '../components/Layout'
import UploadZone from '../components/UploadZone'
import { IconUpload, IconDownload, IconCheck, IconX, IconInfo } from '../components/Icons'
import { downloadCSV, emailsToRecords } from '../utils'

type Status = 'processing' | 'success' | 'error'

interface Result {
  deleted_count: number
  emails: string[]
}

type Step = 1 | 2 | 3

export default function DeleteListGenerator() {
  const [files, setFiles] = useState<File[]>([])
  const [status, setStatus] = useState<{ type: Status; msg: string } | null>(null)
  const [result, setResult] = useState<Result | null>(null)
  const [loading, setLoading] = useState(false)
  const [step, setStep] = useState<Step>(1)

  async function handleProcess() {
    if (!files.length) {
      setStatus({ type: 'error', msg: 'Please select at least one CSV file before processing.' })
      return
    }

    setLoading(true)
    setStep(2)
    setStatus({ type: 'processing', msg: 'Analysing dump files…' })
    setResult(null)

    const form = new FormData()
    files.forEach(f => form.append('files', f))

    try {
      const res = await fetch('/api/upload', { method: 'POST', body: form })
      let data: any
      try { data = await res.json() } catch { throw new Error(`Server error (HTTP ${res.status}) — the file may be unreadable or the server is temporarily unavailable.`) }

      if (!res.ok || data.error) {
        setStatus({ type: 'error', msg: data?.error || `Server error (HTTP ${res.status}).` })
        setStep(1)
      } else if (data.deleted_count === 0) {
        setStatus({ type: 'success', msg: 'Analysis complete — no emails matched the deletion criteria across your uploads.' })
        setStep(1)
      } else {
        setResult(data)
        setStatus({ type: 'success', msg: `Analysis complete.` })
        setStep(3)
      }
    } catch (e: any) {
      setStatus({ type: 'error', msg: e?.message || 'Request failed. Check your connection and try again.' })
      setStep(1)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout
      title="Delete List Generator"
      description="Identify and export inactive email addresses across multiple data dump files."
    >
      {/* Step indicator */}
      <div className="steps">
        <div className={`step ${step >= 1 ? (step > 1 ? 'done' : 'active') : ''}`}>
          <div className="step-num">{step > 1 ? <IconCheck style={{ width: 14, height: 14 }} /> : '1'}</div>
          <div className="step-label">Upload Files</div>
        </div>
        <div className="step-connector" />
        <div className={`step ${step >= 2 ? (step > 2 ? 'done' : 'active') : ''}`}>
          <div className="step-num">{step > 2 ? <IconCheck style={{ width: 14, height: 14 }} /> : '2'}</div>
          <div className="step-label">Process</div>
        </div>
        <div className="step-connector" />
        <div className={`step ${step >= 3 ? 'active' : ''}`}>
          <div className="step-num">3</div>
          <div className="step-label">Download</div>
        </div>
      </div>

      {/* How it works */}
      <div className="card">
        <p className="card-title">How It Works</p>
        <div className="info-strip">
          <IconInfo />
          <p>
            Upload CSV dump files. Each file represents one "dump" period. Any email that appears
            in <strong>3 or more dumps</strong> with a combined total of <strong>0 opens</strong> is
            flagged as inactive and added to the delete list.
            <br />
            <br />
            Required columns: <strong>email</strong>, <strong>opens</strong>.
          </p>
        </div>
      </div>

      {/* Upload */}
      <div className="card">
        <p className="card-title">Upload Dump Files</p>
        <UploadZone
          multiple
          label="Drop your CSV dump files here"
          onFiles={fs => { setFiles(fs); setStatus(null); setResult(null); if (step === 3) setStep(1) }}
        />

        <div className="btn-group">
          <button
            className="btn btn-primary btn-lg"
            onClick={handleProcess}
            disabled={loading || !files.length}
          >
            {loading
              ? <><span className="spinner" />Analysing…</>
              : <><IconUpload style={{ width: 18, height: 18 }} />Process Files</>}
          </button>
        </div>

        {status && (
          <div className={`alert alert-${status.type === 'processing' ? 'loading' : status.type === 'success' ? 'success' : 'error'}`}>
            {status.type === 'processing' && <span className="spinner spinner-muted" />}
            {status.type === 'success' && <IconCheck />}
            {status.type === 'error' && <IconX />}
            {status.msg}
          </div>
        )}
      </div>

      {/* Results */}
      {result && result.deleted_count > 0 && (
        <div className="card">
          <p className="card-title">Results</p>

          <div className="result-banner">
            <div className="result-banner-count">
              <div className="result-banner-number">{result.deleted_count.toLocaleString()}</div>
              <div className="result-banner-label">Emails flagged for deletion</div>
            </div>
            <button
              className="btn btn-outline-green"
              style={{ background: 'rgba(255,255,255,0.12)', border: '1px solid rgba(255,255,255,0.2)', color: '#fff' }}
              onClick={() => downloadCSV('delete_list.csv', emailsToRecords(result.emails))}
            >
              <IconDownload />
              Download delete_list.csv
            </button>
          </div>

          {/* Preview table */}
          <div className="result-table-wrap">
            <table className="result-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Email Address</th>
                </tr>
              </thead>
              <tbody>
                {result.emails.slice(0, 20).map((email, i) => (
                  <tr key={email}>
                    <td style={{ color: 'var(--text-faint)', width: 48 }}>{i + 1}</td>
                    <td>{email}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="table-footer">
              {result.deleted_count > 20
                ? `Showing 20 of ${result.deleted_count.toLocaleString()} emails — download CSV for full list`
                : `${result.deleted_count} email${result.deleted_count !== 1 ? 's' : ''} in total`}
            </div>
          </div>

          <div className="btn-group">
            <button
              className="btn btn-primary"
              onClick={() => downloadCSV('delete_list.csv', emailsToRecords(result.emails))}
            >
              <IconDownload />
              Download CSV
            </button>
          </div>
        </div>
      )}
    </Layout>
  )
}

