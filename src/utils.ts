/** Safely convert an unknown value to a CSV-safe quoted string. */
function escapeCell(value: unknown): string {
  return `"${String(value ?? '').replace(/"/g, '""')}"`
}

/** Trigger a browser download of a CSV file from an array of row objects. */
export function downloadCSV(filename: string, records: Record<string, unknown>[]): void {
  if (!records.length) return

  const headers = Object.keys(records[0])
  const lines = [
    headers.map(escapeCell).join(','),
    ...records.map(row => headers.map(h => escapeCell(row[h])).join(',')),
  ]

  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

/** Wrap a plain string array as email-column records for CSV download. */
export function emailsToRecords(emails: string[]): Record<string, unknown>[] {
  return emails.map(e => ({ email: e }))
}
