/*
  Result.tsx — the screen that matters.

  Layout is deliberate: the photograph sits next to the table of what the AI read
  off it, so anyone can check the reading against the evidence. Below that, every
  rule with its verdict and the reason for it. Nothing here is a black box.
*/

import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  BadgeCheck,
  Download,
  FileText,
  Info,
  ScanLine,
  ShieldQuestion,
  Sparkles,
} from 'lucide-react'
import { getInspection, reportUrl } from '../api'
import type { CheckResult, ExtractedData, InspectionDetail, RuleCheck } from '../types'
import {
  Band,
  ButtonLink,
  ErrorNote,
  RESULT_STYLE,
  SOURCE_STYLE,
  STATUS_STYLE,
  formatDate,
} from '../ui'

/* The order declarations are shown in, and the label for each. Mirrors the
   order a person reads a label, not the order the JSON happens to be in. */
const FIELDS: { key: keyof ExtractedData; label: string }[] = [
  { key: 'product_name', label: 'Product name' },
  { key: 'common_generic_name', label: 'Common / generic name' },
  { key: 'manufacturer_name', label: 'Manufacturer' },
  { key: 'manufacturer_address', label: 'Address' },
  { key: 'packer_name', label: 'Packer' },
  { key: 'importer_name', label: 'Importer' },
  { key: 'net_quantity', label: 'Net quantity' },
  { key: 'mrp', label: 'MRP' },
  { key: 'mrp_text_verbatim', label: 'MRP, exactly as printed' },
  { key: 'date_of_packing', label: 'Date of packing' },
  { key: 'consumer_care', label: 'Consumer care' },
  { key: 'country_of_origin', label: 'Country of origin' },
]

/* Checks are grouped by verdict, worst first: an inspector wants the problems
   at the top, not rule 1 at the top. */
const GROUPS: { result: CheckResult; heading: string; note: string }[] = [
  { result: 'FAIL', heading: 'Failed checks', note: 'The label shows something that does not meet the rule.' },
  {
    result: 'REVIEW',
    heading: 'Needs a physical check',
    note: 'Either the declaration is not visible in this photograph, or the rule needs a measurement a photo cannot give.',
  },
  { result: 'PASS', heading: 'Passed checks', note: 'The declaration is present and in the expected form.' },
  { result: 'NOT_APPLICABLE', heading: 'Not applicable', note: 'This rule only applies to certain packages.' },
]

function CheckRow({ check }: { check: RuleCheck }) {
  const style = RESULT_STYLE[check.result]
  return (
    <li className={`rounded-lg p-6 ${style.tint}`}>
      <div className="flex flex-wrap items-start gap-4">
        <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${style.block}`}>
          <style.Icon className="h-5 w-5 text-white" strokeWidth={2.5} />
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded bg-ink px-1.5 py-0.5 text-xs font-bold text-white">{check.rule_id}</span>
            <h4 className="text-lg font-bold">{check.name}</h4>
          </div>

          <p className="mt-2 leading-relaxed text-gray-700">{check.reason}</p>

          {check.observed && (
            <p className="mt-3 text-sm text-gray-600">
              On the label:{' '}
              <span className="rounded bg-white px-2 py-1 font-semibold text-ink">{check.observed}</span>
            </p>
          )}

          <p className="mt-4 text-sm leading-relaxed text-gray-600">
            <span className="font-semibold">{check.rule_reference}</span> — {check.requirement}
            {!check.citation_verified && (
              <span className="ml-2 rounded bg-accent-tint px-1.5 py-0.5 text-xs font-semibold text-accent-dark">
                citation not yet verified against the official text
              </span>
            )}
          </p>
        </div>

        <span className={`shrink-0 text-sm font-bold ${style.text}`}>{style.label}</span>
      </div>
    </li>
  )
}

export default function Result() {
  const { id } = useParams<{ id: string }>()
  const [inspection, setInspection] = useState<InspectionDetail | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setInspection(null)
    setError(null)
    getInspection(Number(id))
      .then(setInspection)
      .catch((issue: Error) => setError(issue.message))
  }, [id])

  if (error) {
    return (
      <Band>
        <ErrorNote message={error} />
        <div className="mt-8">
          <ButtonLink to="/history" variant="secondary">
            <ArrowLeft className="h-5 w-5" strokeWidth={2.5} />
            Back to history
          </ButtonLink>
        </div>
      </Band>
    )
  }

  if (!inspection) {
    return (
      <Band>
        <p className="text-lg text-gray-500">Loading inspection…</p>
      </Band>
    )
  }

  const status = STATUS_STYLE[inspection.status]
  const sourceNote = SOURCE_STYLE[inspection.source]
  const { compliance } = inspection

  return (
    <>
      {/* ---------------- Verdict block ---------------- */}
      <Band className={`${status.block} text-white`} decorated>
        <Link
          to="/history"
          className="mb-8 inline-flex items-center gap-2 text-sm font-semibold text-white/80 transition-all duration-200 hover:text-white"
        >
          <ArrowLeft className="h-4 w-4" strokeWidth={2.5} />
          All inspections
        </Link>

        <div className="flex flex-wrap items-end justify-between gap-8">
          <div className="max-w-2xl">
            <p className="mb-3 inline-flex items-center gap-2 rounded-lg bg-white/15 px-3 py-1.5 text-sm font-semibold tracking-wider uppercase">
              <status.Icon className="h-4 w-4" strokeWidth={2.5} />
              {status.label}
            </p>
            <h1 className="text-4xl leading-tight font-extrabold md:text-5xl">
              {inspection.product_name || 'Unnamed product'}
            </h1>
            <p className="mt-3 text-lg text-white/90">
              {inspection.manufacturer || 'Manufacturer not declared'} · Inspected {formatDate(inspection.scan_date)}
            </p>
            <p className="mt-6 max-w-xl leading-relaxed text-white/90">{compliance.status_reason}</p>
          </div>

          <div className="rounded-lg bg-white/15 p-6 text-center">
            <p className="text-6xl font-extrabold">{inspection.score}</p>
            <p className="mt-1 text-sm font-semibold tracking-wider uppercase">out of 100</p>
            <p className="mt-4 max-w-40 text-xs leading-relaxed text-white/80">
              Declaration completeness, not the verdict. The verdict is above.
            </p>
          </div>
        </div>

        <div className="mt-10 grid gap-3 sm:grid-cols-4">
          {[
            { value: compliance.passed, label: 'Passed' },
            { value: compliance.failed, label: 'Failed' },
            { value: compliance.review, label: 'To review' },
            { value: compliance.not_applicable, label: 'Not applicable' },
          ].map((tally) => (
            <div key={tally.label} className="rounded-lg bg-white/15 p-4">
              <p className="text-3xl font-extrabold">{tally.value}</p>
              <p className="text-sm font-semibold tracking-wider uppercase">{tally.label}</p>
            </div>
          ))}
        </div>
      </Band>

      {/* ---------------- Honesty banner ---------------- */}
      {sourceNote && (
        <div className="bg-accent">
          <div className="mx-auto flex max-w-7xl items-start gap-3 px-6 py-6">
            <Info className="mt-0.5 h-5 w-5 shrink-0 text-ink" strokeWidth={2.5} />
            <p className="leading-relaxed text-ink">
              <strong className="font-extrabold">{sourceNote.label}.</strong> {sourceNote.detail}
            </p>
          </div>
        </div>
      )}

      {/* ---------------- Evidence: photo beside the reading ---------------- */}
      <Band>
        <div className="grid gap-4 lg:grid-cols-5">
          <div className="lg:col-span-2">
            <p className="mb-2 text-sm font-semibold tracking-wider text-primary uppercase">The evidence</p>
            <h2 className="text-2xl font-extrabold">What we looked at</h2>

            {inspection.image_url ? (
              <img
                src={inspection.image_url}
                alt={`Label of ${inspection.product_name}`}
                className="mt-6 w-full rounded-lg bg-muted"
              />
            ) : (
              <p className="mt-6 rounded-lg bg-muted p-8 text-center text-gray-500">
                No image was stored for this inspection.
              </p>
            )}

            <div className="mt-4 rounded-lg bg-muted p-6 text-sm leading-relaxed text-gray-600">
              <p>
                <span className="font-semibold text-ink">Image quality:</span>{' '}
                {inspection.extracted.image_quality ?? 'not reported'}
              </p>
              <p className="mt-1">
                <span className="font-semibold text-ink">All declarations legible:</span>{' '}
                {inspection.extracted.all_declarations_legible === null
                  ? 'not reported'
                  : inspection.extracted.all_declarations_legible
                    ? 'yes'
                    : 'no'}
              </p>
              {inspection.extracted.overall_confidence !== null && (
                <p className="mt-1">
                  <span className="font-semibold text-ink">Reading confidence:</span>{' '}
                  {Math.round(inspection.extracted.overall_confidence * 100)}%
                </p>
              )}
              {inspection.model_used && (
                <p className="mt-1">
                  <span className="font-semibold text-ink">Read by:</span> {inspection.model_used}
                </p>
              )}
              {inspection.extracted.notes && <p className="mt-3 italic">{inspection.extracted.notes}</p>}
            </div>
          </div>

          <div className="lg:col-span-3">
            <p className="mb-2 text-sm font-semibold tracking-wider text-primary uppercase">The reading</p>
            <h2 className="text-2xl font-extrabold">What the AI found printed on it</h2>
            <p className="mt-3 text-gray-600">
              Blank means the model could not see that declaration. It is instructed to leave a field empty rather than
              fill it in.
            </p>

            <dl className="mt-6 overflow-hidden rounded-lg">
              {FIELDS.map((field, index) => {
                const value = inspection.extracted[field.key]
                return (
                  <div
                    key={field.key}
                    className={`grid gap-1 p-4 sm:grid-cols-3 sm:gap-4 ${index % 2 === 0 ? 'bg-muted' : 'bg-white'}`}
                  >
                    <dt className="text-sm font-semibold tracking-wide text-gray-500 uppercase">{field.label}</dt>
                    <dd className="sm:col-span-2">
                      {value === null || value === '' ? (
                        <span className="text-sm font-semibold text-gray-400">— not found in the image</span>
                      ) : (
                        <span className="font-semibold break-words">{String(value)}</span>
                      )}
                    </dd>
                  </div>
                )
              })}
            </dl>

            <div className="mt-6 flex flex-wrap gap-4">
              <a
                href={reportUrl(inspection.id)}
                target="_blank"
                rel="noreferrer"
                className="inline-flex h-14 items-center justify-center gap-2 rounded-lg bg-primary px-6 font-semibold text-white transition-all duration-200 hover:scale-105 hover:bg-primary-dark"
              >
                <Download className="h-5 w-5" strokeWidth={2.5} />
                Download the PDF report
              </a>
              <ButtonLink to="/scan" variant="outline">
                <ScanLine className="h-5 w-5" strokeWidth={2.5} />
                Scan another package
              </ButtonLink>
            </div>
          </div>
        </div>
      </Band>

      {/* ---------------- Plain-language explanation ---------------- */}
      {inspection.explanation && (
        <Band className="bg-ink text-white">
          <div className="max-w-3xl">
            <p className="mb-2 flex items-center gap-2 text-sm font-semibold tracking-wider text-primary uppercase">
              <Sparkles className="h-4 w-4" strokeWidth={2.5} />
              In plain language
            </p>
            <h2 className="text-3xl font-extrabold">What this means</h2>
            <p className="mt-6 text-lg leading-relaxed whitespace-pre-line text-gray-300">{inspection.explanation}</p>
            <p className="mt-8 border-t-2 border-white/10 pt-6 text-sm leading-relaxed text-gray-400">
              This paragraph was written by the AI <em>after</em> the rule engine had already decided. It was given the
              finished results and asked only to phrase them — it cannot change a verdict.
            </p>
          </div>
        </Band>
      )}

      {/* ---------------- Every check ---------------- */}
      <Band className="bg-muted">
        <div className="mb-8">
          <p className="mb-2 flex items-center gap-2 text-sm font-semibold tracking-wider text-primary uppercase">
            <BadgeCheck className="h-4 w-4" strokeWidth={2.5} />
            Rule by rule
          </p>
          <h2 className="text-3xl font-extrabold md:text-4xl">All {compliance.checks.length} checks</h2>
          <p className="mt-3 max-w-3xl text-lg text-gray-600">
            Each one is a few lines of Python in <code className="font-semibold">backend/compliance.py</code>, reading{' '}
            <code className="font-semibold">backend/rules.json</code>. Run the same reading twice and you get the same
            answer twice.
          </p>
        </div>

        <div className="space-y-10">
          {GROUPS.map((group) => {
            const checks = compliance.checks.filter((check) => check.result === group.result)
            if (checks.length === 0) return null
            return (
              <div key={group.result}>
                <h3 className="text-xl font-bold">
                  {group.heading} <span className="text-gray-400">({checks.length})</span>
                </h3>
                <p className="mt-1 max-w-2xl text-sm text-gray-600">{group.note}</p>
                <ul className="mt-5 space-y-3">
                  {checks.map((check) => (
                    <CheckRow key={check.rule_id} check={check} />
                  ))}
                </ul>
              </div>
            )
          })}
        </div>
      </Band>

      {/* ---------------- Disclaimer ---------------- */}
      <Band className="bg-accent text-ink">
        <div className="flex max-w-4xl gap-4">
          <ShieldQuestion className="mt-1 h-8 w-8 shrink-0" strokeWidth={2.5} />
          <div>
            <h2 className="text-2xl font-extrabold">This is decision support, not a legal determination.</h2>
            <p className="mt-3 leading-relaxed">
              A photograph shows a few panels of a package. Letter height, principal display panel area and standard
              pack sizes need the physical package in hand. Findings marked <strong>needs a physical check</strong> are
              exactly that: things a human inspector still has to confirm. Nothing on this page replaces an official
              inspection.
            </p>
            <p className="mt-4 flex items-center gap-2 text-sm font-semibold">
              <FileText className="h-4 w-4" strokeWidth={2.5} />
              The same wording appears on the PDF report.
            </p>
          </div>
        </div>
      </Band>
    </>
  )
}
