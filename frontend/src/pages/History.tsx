/*
  History.tsx — every inspection in the database, newest first.

  Filtering happens on the server (GET /api/inspections?status=...) rather than
  in the browser, so the list stays correct however many rows exist.
*/

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Download, FileText, ScanLine } from 'lucide-react'
import { getInspections, reportUrl } from '../api'
import type { InspectionSummary, Status } from '../types'
import { Band, ButtonLink, ErrorNote, SOURCE_STYLE, STATUS_STYLE, StatusBadge, formatDate } from '../ui'

const FILTERS: { value: Status | 'ALL'; label: string }[] = [
  { value: 'ALL', label: 'Everything' },
  { value: 'COMPLIANT', label: 'Compliant' },
  { value: 'NEEDS_REVIEW', label: 'Needs review' },
  { value: 'POTENTIAL_VIOLATION', label: 'Potential violation' },
]

export default function History() {
  const [filter, setFilter] = useState<Status | 'ALL'>('ALL')
  const [inspections, setInspections] = useState<InspectionSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setInspections(null)
    setError(null)
    getInspections(filter === 'ALL' ? undefined : filter)
      .then(setInspections)
      .catch((issue: Error) => setError(issue.message))
  }, [filter])

  const hasSampleRows = inspections?.some((row) => row.source !== 'live_ai') ?? false

  return (
    <>
      <Band className="bg-ink text-white" decorated>
        <div className="flex flex-wrap items-end justify-between gap-8">
          <div className="max-w-2xl">
            <p className="mb-4 inline-block rounded-lg bg-white/15 px-3 py-1.5 text-sm font-semibold tracking-wider uppercase">
              Inspection history
            </p>
            <h1 className="text-4xl font-extrabold md:text-5xl">Everything that has been checked</h1>
            <p className="mt-4 text-lg text-gray-300">
              Stored in a local SQLite file, one row per inspection. Click any row to see the full breakdown, or pull
              the PDF straight from the list.
            </p>
          </div>
          <ButtonLink to="/scan" variant="secondary">
            <ScanLine className="h-5 w-5" strokeWidth={2.5} />
            New scan
          </ButtonLink>
        </div>
      </Band>

      <Band>
        {/* Filter chips */}
        <div className="mb-8 flex flex-wrap gap-3">
          {FILTERS.map((option) => {
            const active = filter === option.value
            return (
              <button
                key={option.value}
                onClick={() => setFilter(option.value)}
                className={`h-12 rounded-lg px-5 font-semibold transition-all duration-200 hover:scale-105 ${
                  active ? 'bg-primary text-white' : 'bg-muted text-ink hover:bg-line'
                }`}
              >
                {option.label}
              </button>
            )
          })}
        </div>

        {error && <ErrorNote message={error} />}

        {inspections === null && !error && <p className="text-lg text-gray-500">Loading inspections…</p>}

        {inspections !== null && inspections.length === 0 && (
          <div className="rounded-lg bg-muted p-12 text-center">
            <p className="text-xl font-bold">Nothing here yet</p>
            <p className="mx-auto mt-2 max-w-md text-gray-600">
              {filter === 'ALL'
                ? 'Run a scan — or one of the demo products, which needs no API key — and it will show up here.'
                : 'No inspection currently has that status.'}
            </p>
            <div className="mt-8 flex justify-center">
              <ButtonLink to="/scan">
                <ScanLine className="h-5 w-5" strokeWidth={2.5} />
                Scan a package
              </ButtonLink>
            </div>
          </div>
        )}

        {inspections !== null && inspections.length > 0 && (
          <>
            <p className="mb-4 text-sm font-semibold tracking-wider text-gray-500 uppercase">
              {inspections.length} {inspections.length === 1 ? 'inspection' : 'inspections'}
              {hasSampleRows && ' · includes demo and sample rows, each labelled below'}
            </p>

            {/* A flat table on wide screens; the same rows stack on a phone. */}
            <div className="overflow-x-auto rounded-lg">
              {/* min-w keeps the columns readable on a phone; the wrapper scrolls. */}
              <table className="w-full min-w-[48rem] border-collapse text-left">
                <thead>
                  <tr className="bg-ink text-white">
                    <th className="p-4 text-sm font-semibold tracking-wider uppercase">#</th>
                    <th className="p-4 text-sm font-semibold tracking-wider uppercase">Product</th>
                    <th className="p-4 text-sm font-semibold tracking-wider uppercase">Manufacturer</th>
                    <th className="p-4 text-sm font-semibold tracking-wider uppercase">Inspected</th>
                    <th className="p-4 text-sm font-semibold tracking-wider uppercase">Score</th>
                    <th className="p-4 text-sm font-semibold tracking-wider uppercase">Verdict</th>
                    <th className="p-4 text-sm font-semibold tracking-wider uppercase">Report</th>
                  </tr>
                </thead>
                <tbody>
                  {inspections.map((row, index) => {
                    const sourceNote = SOURCE_STYLE[row.source]
                    return (
                      <tr key={row.id} className={index % 2 === 0 ? 'bg-muted' : 'bg-white'}>
                        <td className="p-4 font-bold text-gray-400">{row.id}</td>
                        <td className="p-4">
                          <Link
                            to={`/result/${row.id}`}
                            className="font-semibold text-primary transition-all duration-200 hover:underline"
                          >
                            {row.product_name || 'Unnamed product'}
                          </Link>
                          {sourceNote && (
                            <span className="mt-1 block text-xs font-semibold tracking-wide text-gray-500 uppercase">
                              {sourceNote.label}
                            </span>
                          )}
                        </td>
                        <td className="p-4 text-gray-600">{row.manufacturer || '—'}</td>
                        <td className="p-4 text-sm text-gray-600">{formatDate(row.scan_date)}</td>
                        <td className={`p-4 text-lg font-bold ${STATUS_STYLE[row.status].text}`}>{row.score}</td>
                        <td className="p-4">
                          <StatusBadge status={row.status} />
                        </td>
                        <td className="p-4">
                          <a
                            href={reportUrl(row.id)}
                            target="_blank"
                            rel="noreferrer"
                            title={`Download the PDF report for inspection ${row.id}`}
                            className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-white text-primary transition-all duration-200 hover:scale-110 hover:bg-primary hover:text-white"
                          >
                            <Download className="h-5 w-5" strokeWidth={2.5} />
                          </a>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            <p className="mt-6 flex items-start gap-3 text-sm leading-relaxed text-gray-600">
              <FileText className="mt-0.5 h-4 w-4 shrink-0" strokeWidth={2.5} />
              Reports are generated on request from the stored reading, so a report always matches the inspection it
              came from.
            </p>
          </>
        )}
      </Band>
    </>
  )
}
