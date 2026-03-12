import { useState } from 'react'
import Layout from '../components/Layout'
import UploadZone from '../components/UploadZone'
import { IconDownload, IconInfo, IconLayers } from '../components/Icons'
import { downloadCSV, emailsToRecords } from '../utils'

interface Result {
  csv1_total: number
  csv2_total: number
  overlap_count: number
  remaining_count: number
  emails: string[]
}

export default function OverlapChecker() {
  const [file1, setFile1] = useState<File | null>(null)
  const [file2, setFile2] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<Result | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleProcess() {
    if (!file1 || !file2) {
      setError('Please upload both CSV files before running.')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    const form = new FormData()
    form.append('file1', file1)
    form.append('file2', file2)

    try {
      const res = await fetch('/api/overlap-checker', { method: 'POST', body: form })
      let data: any
      try { data = await res.json() } catch { throw new Error(`Server error (HTTP ${res.status}) — the file may be unreadable or the server is temporarily unavailable.`) }

      if (!res.ok || data.error) {
        setError(data?.error || `Server error (HTTP ${res.status}).`)
      } else {
        setResult(data)
      }
    } catch (e: any) {
      setError(e?.message || 'Processing failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout
      title="Overlap Checker"
      description="Remove overlapping emails between two CSV files and download the clean remaining list."
    >
      {/* Info strip */}
      <div className="info-strip">
        <span className="info-strip-icon"><IconInfo /></span>
        <div>
          <strong>How it works:</strong> Upload two CSVs with an <code>email</code> column.
          Emails found in <strong>CSV 2</strong> are removed from <strong>CSV 1</strong>.
          The clean, non-overlapping list is yours to download immediately.
        </div>
      </div>

      {/* Step indicator */}
      <div className="steps">
        <div className={`step ${file1 || file2 ? 'done' : 'active'}`}>
          <div className="step-num">1</div>
          <div className="step-label">Upload CSVs</div>
        </div>
        <div className="step-connector" />
        <div className={`step ${loading ? 'active' : result ? 'done' : ''}`}>
          <div className="step-num">2</div>
          <div className="step-label">Process</div>
        </div>
        <div className="step-connector" />
        <div className={`step ${result ? 'active' : ''}`}>
          <div className="step-num">3</div>
          <div className="step-label">Download</div>
        </div>
      </div>

      {/* Upload section */}
      <div className="upload-pair">
        <div className="upload-col">
          <p className="upload-col-label">
            <IconLayers />
            <span>CSV 1 — Main List</span>
          </p>
          <p className="upload-col-hint">The list you want to filter</p>
          <UploadZone
            label="Upload CSV 1"
            description="Main email list"
            onFiles={([f]) => setFile1(f ?? null)}
          />
        </div>
        <div className="upload-col-divider">
          <span>minus</span>
        </div>
        <div className="upload-col">
          <p className="upload-col-label">
            <IconLayers />
            <span>CSV 2 — Overlap List</span>
          </p>
          <p className="upload-col-hint">Emails to remove from CSV 1</p>
          <UploadZone
            label="Upload CSV 2"
            description="Emails to subtract"
            onFiles={([f]) => setFile2(f ?? null)}
          />
        </div>
      </div>

      {error && (
        <div className="alert alert-error">
          <strong>Error:</strong> {error}
        </div>
      )}

      <div style={{ textAlign: 'center', marginTop: 8 }}>
        <button
          className="btn btn-primary btn-lg"
          onClick={handleProcess}
          disabled={loading}
        >
          {loading ? (
            <>
              <span className="spinner" />
              Checking overlap…
            </>
          ) : (
            'Check Overlap'
          )}
        </button>
      </div>

      {/* Results */}
      {result && (
        <div className="result-section">
          {/* Venn diagram */}
          <div className="overlap-visual">
            <div className="overlap-circle overlap-circle-1">
              <div className="overlap-circle-num">{result.csv1_total.toLocaleString()}</div>
              CSV 1
            </div>
            <div className="overlap-middle">
              <div className="overlap-middle-num">{result.overlap_count.toLocaleString()}</div>
              overlap
            </div>
            <div className="overlap-circle overlap-circle-2">
              <div className="overlap-circle-num">{result.csv2_total.toLocaleString()}</div>
              CSV 2
            </div>
          </div>

          {/* Stats grid */}
          <div className="stats-grid">
            <div className="stat-box">
              <div className="stat-box-number">{result.csv1_total.toLocaleString()}</div>
              <div className="stat-box-label">CSV 1 Emails</div>
            </div>
            <div className="stat-box">
              <div className="stat-box-number">{result.csv2_total.toLocaleString()}</div>
              <div className="stat-box-label">CSV 2 Emails</div>
            </div>
            <div className="stat-box">
              <div className="stat-box-number accent">{result.overlap_count.toLocaleString()}</div>
              <div className="stat-box-label">Overlapping</div>
            </div>
            <div className="stat-box">
              <div className="stat-box-number">{result.remaining_count.toLocaleString()}</div>
              <div className="stat-box-label">Remaining</div>
            </div>
          </div>

          {result.remaining_count > 0 ? (
            <>
              <div className="result-banner">
                <div className="result-banner-text">
                  <strong>{result.remaining_count.toLocaleString()}</strong> emails remaining
                  after removing <strong>{result.overlap_count.toLocaleString()}</strong> overlaps
                </div>
                <button
                  className="btn btn-outline-green"
                  onClick={() =>
                    downloadCSV('overlap_filtered.csv', emailsToRecords(result.emails))
                  }
                >
                  <IconDownload />
                  Download Filtered List
                </button>
              </div>
            </>
          ) : (
            <div className="alert alert-info" style={{ marginTop: 24 }}>
              All emails from CSV 1 were found in CSV 2 — nothing remains after filtering.
            </div>
          )}
        </div>
      )}
    </Layout>
  )
}
