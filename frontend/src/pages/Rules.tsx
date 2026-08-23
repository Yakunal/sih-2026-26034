/*
  Rules.tsx — the page for the judges.

  It shows exactly which rules we implemented, how each one is checked, what it
  is worth in the score, and whether we have verified its citation against the
  official text yet. A rule we could not implement correctly is not here, and
  that is the point.
*/

import { useEffect, useState } from 'react'
import { AlertTriangle, Calculator, FileWarning, Hand, Regex, ShieldCheck, ToggleRight } from 'lucide-react'
import { getRules } from '../api'
import type { Rule, RulesResponse } from '../types'
import { Band, ErrorNote, SectionTitle } from '../ui'

/** How each check type is described and coloured. Matches compliance.py. */
const CHECK_TYPE: Record<string, { label: string; explain: string; block: string; Icon: typeof ShieldCheck }> = {
  presence: {
    label: 'Presence',
    explain: 'The declaration has to be there. Passes if the field, or any acceptable alternative, is non-empty.',
    block: 'bg-primary',
    Icon: ShieldCheck,
  },
  format: {
    label: 'Format',
    explain: 'The declaration is there — this checks that it is written in the form the rule requires.',
    block: 'bg-secondary',
    Icon: Regex,
  },
  conditional_presence: {
    label: 'Conditional',
    explain: 'Only required when something else is true. Otherwise it is marked not applicable, not failed.',
    block: 'bg-accent',
    Icon: ToggleRight,
  },
  manual: {
    label: 'Manual',
    explain: 'Cannot be decided from a photograph. Always returns "needs a physical check" and is left out of the score.',
    block: 'bg-gray-500',
    Icon: Hand,
  },
}

function RuleCard({ rule }: { rule: Rule }) {
  const type = CHECK_TYPE[rule.check] ?? CHECK_TYPE.presence
  return (
    <div className="rounded-lg bg-muted p-6 md:p-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-lg ${type.block}`}>
            <type.Icon className="h-6 w-6 text-white" strokeWidth={2.5} />
          </span>
          <div>
            <span className="rounded bg-ink px-1.5 py-0.5 text-xs font-bold text-white">{rule.id}</span>
            <h3 className="mt-1 text-lg font-bold">{rule.name}</h3>
          </div>
        </div>

        <div className="text-right">
          <p className="text-sm font-semibold tracking-wider text-gray-500 uppercase">{type.label}</p>
          <p className="text-sm text-gray-500">
            {rule.weight === 0 ? 'not scored' : `weight ${rule.weight}`}
          </p>
        </div>
      </div>

      <p className="mt-5 leading-relaxed text-gray-700">{rule.requirement}</p>

      <dl className="mt-5 space-y-1 text-sm text-gray-600">
        <div className="flex gap-2">
          <dt className="font-semibold text-ink">Legal reference:</dt>
          <dd>{rule.rule_reference}</dd>
        </div>
        <div className="flex gap-2">
          <dt className="font-semibold text-ink">Reads field:</dt>
          <dd>
            <code>{rule.field}</code>
            {rule.alt_fields.length > 0 && <> (or {rule.alt_fields.map((f) => <code key={f}>{f}</code>)})</>}
          </dd>
        </div>
        {rule.trigger_field && (
          <div className="flex gap-2">
            <dt className="font-semibold text-ink">Only when set:</dt>
            <dd>
              <code>{rule.trigger_field}</code>
            </dd>
          </div>
        )}
        {rule.pattern && (
          <div className="flex gap-2">
            <dt className="font-semibold text-ink">Pattern:</dt>
            <dd>
              <code className="break-all">{rule.pattern}</code>
            </dd>
          </div>
        )}
      </dl>

      <div className="mt-5 flex flex-wrap gap-2 border-t-2 border-line pt-5">
        {rule.escalates ? (
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-danger-tint px-3 py-1.5 text-xs font-semibold text-danger-dark">
            <AlertTriangle className="h-3.5 w-3.5" strokeWidth={2.5} />
            Failing this is a potential violation
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-accent-tint px-3 py-1.5 text-xs font-semibold text-accent-dark">
            Failing this only flags a review
          </span>
        )}

        {!rule.citation_verified && (
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-1.5 text-xs font-semibold text-gray-600">
            <FileWarning className="h-3.5 w-3.5" strokeWidth={2.5} />
            Citation not yet verified
          </span>
        )}
      </div>
    </div>
  )
}

export default function Rules() {
  const [data, setData] = useState<RulesResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getRules()
      .then(setData)
      .catch((issue: Error) => setError(issue.message))
  }, [])

  return (
    <>
      <Band className="bg-primary text-white" decorated>
        <div className="max-w-3xl">
          <p className="mb-4 inline-block rounded-lg bg-white/15 px-3 py-1.5 text-sm font-semibold tracking-wider uppercase">
            The rule engine
          </p>
          <h1 className="text-4xl font-extrabold md:text-5xl">
            {data ? data.total : 'Fifteen'} rules, all of them plain Python
          </h1>
          <p className="mt-6 text-lg leading-relaxed text-white/90">
            The Legal Metrology (Packaged Commodities) Rules, 2011 are much larger than this. We implemented the subset
            we could implement correctly from a photograph — and we say so rather than approximating the rest.
          </p>
        </div>

        {data && (
          <div className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { value: data.total, label: 'Rules implemented' },
              { value: data.scoreable, label: 'Counted in the score' },
              { value: data.manual, label: 'Need a physical check' },
              { value: data.unverified_citations, label: 'Citations still to verify' },
            ].map((item) => (
              <div key={item.label} className="rounded-lg bg-white/15 p-5">
                <p className="text-4xl font-extrabold">{item.value}</p>
                <p className="mt-1 text-sm font-semibold tracking-wider uppercase">{item.label}</p>
              </div>
            ))}
          </div>
        )}
      </Band>

      {/* ---------------- Scoring, stated plainly ---------------- */}
      <Band className="bg-ink text-white">
        <div className="grid gap-4 lg:grid-cols-2">
          <div>
            <p className="mb-2 flex items-center gap-2 text-sm font-semibold tracking-wider text-primary uppercase">
              <Calculator className="h-4 w-4" strokeWidth={2.5} />
              Scoring
            </p>
            <h2 className="text-3xl font-extrabold">How the number is worked out</h2>
            <p className="mt-6 rounded-lg bg-white/5 p-6 font-mono text-lg break-words">
              {data?.scoring_formula ?? 'score = 100 × earned weight ÷ scoreable weight'}
            </p>
            <ul className="mt-6 space-y-3 leading-relaxed text-gray-300">
              <li>
                Presence rules weigh <strong className="text-white">2</strong>, format rules{' '}
                <strong className="text-white">1</strong>, manual rules{' '}
                <strong className="text-white">0</strong> — a rule we cannot judge from a photo cannot move the score.
              </li>
              <li>
                Rules that come back <em>needs review</em> or <em>not applicable</em> are removed from both sides of the
                fraction, so an unreadable panel does not quietly count as a pass or a fail.
              </li>
              <li>
                The score measures <strong className="text-white">completeness of the declarations we could read</strong>
                . The verdict is a separate judgement — a package can score well and still be flagged.
              </li>
            </ul>
          </div>

          <div>
            <p className="mb-2 text-sm font-semibold tracking-wider text-primary uppercase">Verdicts</p>
            <h2 className="text-3xl font-extrabold">Absence of evidence is not evidence of a defect</h2>
            <div className="mt-6 space-y-3">
              <div className="rounded-lg bg-white/5 p-6">
                <p className="font-bold text-secondary">COMPLIANT</p>
                <p className="mt-1 leading-relaxed text-gray-300">
                  Nothing failed, and nothing mandatory was missing. Manual items are still listed for the inspector.
                </p>
              </div>
              <div className="rounded-lg bg-white/5 p-6">
                <p className="font-bold text-accent">NEEDS REVIEW</p>
                <p className="mt-1 leading-relaxed text-gray-300">
                  A required declaration was not visible. One photograph shows one or two panels — it may be printed on
                  a face the camera never saw, so we do not call it a violation.
                </p>
              </div>
              <div className="rounded-lg bg-white/5 p-6">
                <p className="font-bold text-danger">POTENTIAL VIOLATION</p>
                <p className="mt-1 leading-relaxed text-gray-300">
                  We can <em>see</em> the problem: an MRP with no tax wording, "100 gms" instead of "100 g", an
                  impossible date. Also raised when so many declarations are absent that a missed panel no longer
                  explains it.
                </p>
              </div>
            </div>
          </div>
        </div>
      </Band>

      {/* ---------------- The four check types ---------------- */}
      <Band>
        <SectionTitle
          eyebrow="Check types"
          title="Four kinds of check, and that is all"
          lead="Every rule below is one of these four. Each is a small function in backend/compliance.py, picked by name from a dictionary."
        />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Object.entries(CHECK_TYPE).map(([key, type]) => (
            <div key={key} className="group rounded-lg bg-muted p-6 transition-all duration-200 hover:scale-[1.02]">
              <span className={`flex h-14 w-14 items-center justify-center rounded-lg ${type.block}`}>
                <type.Icon
                  className="h-7 w-7 text-white transition-transform duration-200 group-hover:scale-110"
                  strokeWidth={2.5}
                />
              </span>
              <h3 className="mt-5 text-lg font-bold">{type.label}</h3>
              <p className="mt-2 text-sm leading-relaxed text-gray-600">{type.explain}</p>
            </div>
          ))}
        </div>
      </Band>

      {/* ---------------- The rules themselves ---------------- */}
      <Band className="bg-muted">
        <SectionTitle
          eyebrow="Implemented rules"
          title="Every rule, in full"
          lead="Read straight from backend/rules.json — the same file the engine reads, so this page cannot drift out of date."
        />

        {error && <ErrorNote message={error} />}
        {!data && !error && <p className="text-lg text-gray-500">Loading rules…</p>}

        {data && data.unverified_citations > 0 && (
          <p className="mb-8 flex items-start gap-3 rounded-lg bg-white p-6 leading-relaxed text-gray-700">
            <FileWarning className="mt-0.5 h-5 w-5 shrink-0 text-accent-dark" strokeWidth={2.5} />
            <span>
              <strong>{data.unverified_citations} citations are marked unverified.</strong> The rule numbers come from
              secondary sources; we have not yet checked them against the official gazette text. They are flagged here
              instead of being presented as confirmed, and each will be corrected once the official PDF is in the repo
              at <code className="font-semibold">sample_data/</code>.
            </span>
          </p>
        )}

        {data && (
          <div className="grid gap-4 lg:grid-cols-2">
            {data.rules.map((rule) => (
              <RuleCard key={rule.id} rule={rule} />
            ))}
          </div>
        )}
      </Band>
    </>
  )
}
