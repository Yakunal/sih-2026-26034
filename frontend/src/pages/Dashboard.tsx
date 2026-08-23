/*
  Dashboard.tsx — the landing page.

  Three jobs: say what the tool is, show the numbers from the database, and be
  honest about what the tool cannot do. That last section is deliberate: the
  limits are the strongest thing we have to say about a photograph-based check.
*/

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowRight,
  Ban,
  Camera,
  CheckCircle2,
  FileText,
  HelpCircle,
  Info,
  ListChecks,
  ScanLine,
  Sparkles,
} from 'lucide-react'
import { getHealth, getStats } from '../api'
import type { Health, Stats } from '../types'
import { Band, ButtonLink, ErrorNote, STATUS_STYLE, SectionTitle, StatusBadge, formatDate } from '../ui'

const PIPELINE = [
  {
    Icon: Camera,
    title: 'Photograph the label',
    body: 'Upload a photo of the package, or pick one of the prepared demo products.',
  },
  {
    Icon: Sparkles,
    title: 'The AI reads it',
    body: 'Gemini returns only the declarations it can actually see. Anything it cannot see comes back empty — it never guesses.',
  },
  {
    Icon: ListChecks,
    title: 'The rule engine decides',
    body: 'Fifteen implemented rules run as plain Python. The same reading always gives the same verdict, and the AI has no vote.',
  },
  {
    Icon: FileText,
    title: 'Report and record',
    body: 'The result is scored, saved to the inspection history, and can be downloaded as a PDF.',
  },
]

const LIMITS = [
  {
    title: 'We do not measure font height',
    body: 'Rule 9 sets a minimum letter height in millimetres. That cannot be measured from an arbitrary photograph, so the system reports "needs physical verification" instead of inventing a number.',
  },
  {
    title: 'A missing declaration is not a violation',
    body: 'One photo shows one or two panels. If a declaration is absent we flag it for review, because it may be printed on a face the camera never saw.',
  },
  {
    title: 'The AI never decides compliance',
    body: 'It answers one question: what does the package say? Every verdict comes from the rule engine, which you can read in a single file.',
  },
  {
    title: 'Fifteen rules, not the whole statute',
    body: 'We implemented only the rules we could implement correctly. The Rules page lists every one, with its citation and its type.',
  },
]

function StatCard({
  value,
  label,
  accent,
  Icon,
}: {
  value: number | string
  label: string
  accent: string
  Icon: typeof CheckCircle2
}) {
  return (
    <div className="rounded-lg bg-muted p-6">
      <span className={`mb-4 flex h-14 w-14 items-center justify-center rounded-lg ${accent}`}>
        <Icon className="h-7 w-7 text-white" strokeWidth={2.5} />
      </span>
      <p className="text-4xl font-extrabold md:text-5xl">{value}</p>
      <p className="mt-1 text-sm font-semibold tracking-wider text-gray-500 uppercase">{label}</p>
    </div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [health, setHealth] = useState<Health | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([getStats(), getHealth()])
      .then(([statsData, healthData]) => {
        setStats(statsData)
        setHealth(healthData)
      })
      .catch((issue: Error) => setError(issue.message))
  }, [])

  return (
    <>
      {/* ---------------- Hero: a solid blue poster ---------------- */}
      <Band className="bg-primary text-white" decorated>
        <div className="max-w-3xl">
          <p className="mb-4 inline-block rounded-lg bg-white/15 px-3 py-1.5 text-sm font-semibold tracking-wider uppercase">
            SIH 26034 · Prototype
          </p>
          <h1 className="text-4xl leading-[1.05] font-extrabold md:text-6xl">
            Check a packaged commodity label in about ten seconds.
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-white/90 md:text-xl">
            Photograph the package. The AI reads the declarations; a deterministic rule engine checks them against
            the Legal Metrology (Packaged Commodities) Rules, 2011 and explains every finding.
          </p>
          <div className="mt-10 flex flex-wrap gap-4">
            <ButtonLink to="/scan" variant="secondary">
              <ScanLine className="h-5 w-5" strokeWidth={2.5} />
              Scan a package
            </ButtonLink>
            <ButtonLink to="/rules" variant="outlineLight">
              See the 15 rules
              <ArrowRight className="h-5 w-5" strokeWidth={2.5} />
            </ButtonLink>
          </div>

          {health && !health.ai_configured && (
            <p className="mt-8 flex items-start gap-3 rounded-lg bg-white/15 p-4 text-sm leading-relaxed">
              <Info className="mt-0.5 h-5 w-5 shrink-0" strokeWidth={2.5} />
              <span>
                No Gemini API key is configured, so live scanning is off. <strong>Demo Mode works fully</strong> —
                four prepared products run through the real rule engine.
              </span>
            </p>
          )}
        </div>
      </Band>

      {/* ---------------- Numbers ---------------- */}
      <Band>
        {error && <ErrorNote message={error} />}

        {stats && (
          <>
            <SectionTitle
              eyebrow="Inspection record"
              title="What has been checked so far"
              lead="Every scan is written to a local SQLite database, so the history and these counts come from real rows."
            />

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard value={stats.total} label="Packages inspected" accent="bg-primary" Icon={ScanLine} />
              <StatCard value={stats.compliant} label="Compliant" accent="bg-secondary" Icon={CheckCircle2} />
              <StatCard value={stats.needs_review} label="Need review" accent="bg-accent" Icon={HelpCircle} />
              <StatCard
                value={stats.potential_violations}
                label="Potential violations"
                accent="bg-danger"
                Icon={AlertTriangle}
              />
            </div>

            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div className="rounded-lg bg-ink p-6 text-white">
                <p className="text-sm font-semibold tracking-wider text-gray-400 uppercase">Compliant share</p>
                <p className="mt-2 text-5xl font-extrabold">{stats.compliance_percentage}%</p>
              </div>
              <div className="rounded-lg bg-ink p-6 text-white">
                <p className="text-sm font-semibold tracking-wider text-gray-400 uppercase">Average score</p>
                <p className="mt-2 text-5xl font-extrabold">{stats.average_score}/100</p>
              </div>
            </div>

            {stats.includes_sample_data && (
              <p className="mt-4 flex items-start gap-3 rounded-lg bg-accent-tint p-4 text-sm leading-relaxed text-accent-dark">
                <Info className="mt-0.5 h-5 w-5 shrink-0" strokeWidth={2.5} />
                <span>
                  <strong>Includes sample data.</strong> Some rows were generated to populate this dashboard for the
                  demo. Their rule results were still produced by the real rule engine, and each one is labelled
                  "Sample Data" on its own page.
                </span>
              </p>
            )}

            {/* Most common failures + recent activity, side by side */}
            <div className="mt-12 grid gap-4 lg:grid-cols-2">
              <div className="rounded-lg bg-muted p-6 md:p-8">
                <h3 className="text-xl font-bold">Most frequently failed rules</h3>
                <p className="mt-1 text-sm text-gray-600">Counted across every inspection in the database.</p>

                {stats.common_violations.length === 0 ? (
                  <p className="mt-6 text-gray-600">No failed checks recorded yet.</p>
                ) : (
                  <ul className="mt-6 space-y-3">
                    {stats.common_violations.map((violation) => {
                      const widest = stats.common_violations[0].count
                      return (
                        <li key={violation.rule_id}>
                          <div className="flex items-baseline justify-between gap-4">
                            <p className="font-semibold">
                              <span className="mr-2 rounded bg-ink px-1.5 py-0.5 text-xs font-bold text-white">
                                {violation.rule_id}
                              </span>
                              {violation.name}
                            </p>
                            <span className="font-bold text-danger-dark">{violation.count}</span>
                          </div>
                          {/* A flat bar, not a chart library. */}
                          <div className="mt-1.5 h-2 w-full rounded-full bg-line">
                            <div
                              className="h-2 rounded-full bg-danger"
                              style={{ width: `${(violation.count / widest) * 100}%` }}
                            />
                          </div>
                        </li>
                      )
                    })}
                  </ul>
                )}
              </div>

              <div className="rounded-lg bg-muted p-6 md:p-8">
                <div className="flex items-baseline justify-between gap-4">
                  <h3 className="text-xl font-bold">Recent inspections</h3>
                  <Link to="/history" className="text-sm font-semibold text-primary hover:underline">
                    View all
                  </Link>
                </div>

                {stats.recent.length === 0 ? (
                  <p className="mt-6 text-gray-600">Nothing scanned yet.</p>
                ) : (
                  <ul className="mt-6 space-y-2">
                    {stats.recent.map((inspection) => (
                      <li key={inspection.id}>
                        <Link
                          to={`/result/${inspection.id}`}
                          className="flex items-center justify-between gap-4 rounded-lg bg-white p-4 transition-all duration-200 hover:scale-[1.02]"
                        >
                          <span className="min-w-0">
                            <span className="block truncate font-semibold">{inspection.product_name}</span>
                            <span className="block text-xs text-gray-500">{formatDate(inspection.scan_date)}</span>
                          </span>
                          <span className="flex shrink-0 items-center gap-3">
                            <span className={`font-bold ${STATUS_STYLE[inspection.status].text}`}>
                              {inspection.score}
                            </span>
                            <StatusBadge status={inspection.status} />
                          </span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </>
        )}
      </Band>

      {/* ---------------- How it works: dark block ---------------- */}
      <Band className="bg-ink text-white">
        <p className="mb-2 text-sm font-semibold tracking-wider text-primary uppercase">How it works</p>
        <h2 className="text-3xl font-extrabold md:text-4xl">Four steps, and only one of them is AI.</h2>

        <ol className="mt-12 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {PIPELINE.map(({ Icon, title, body }, index) => (
            <li key={title} className="group rounded-lg bg-white/5 p-6 transition-all duration-200 hover:bg-white/10">
              <div className="flex items-center gap-3">
                <span className="flex h-14 w-14 items-center justify-center rounded-lg bg-white">
                  <Icon className="h-7 w-7 text-primary transition-transform duration-200 group-hover:scale-110" strokeWidth={2.5} />
                </span>
                <span className="text-4xl font-extrabold text-white/20">{index + 1}</span>
              </div>
              <h3 className="mt-5 text-lg font-bold">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-gray-300">{body}</p>
            </li>
          ))}
        </ol>
      </Band>

      {/* ---------------- Limits: amber block ---------------- */}
      <Band className="bg-accent text-ink">
        <p className="mb-2 flex items-center gap-2 text-sm font-semibold tracking-wider uppercase">
          <Ban className="h-4 w-4" strokeWidth={3} />
          Known limits
        </p>
        <h2 className="text-3xl font-extrabold md:text-4xl">What this system deliberately will not do.</h2>
        <p className="mt-3 max-w-3xl text-lg">
          A tool that guesses is worse than a tool that says "I cannot tell from this photograph".
        </p>

        <div className="mt-12 grid gap-4 md:grid-cols-2">
          {LIMITS.map(({ title, body }) => (
            <div key={title} className="rounded-lg bg-white p-6 md:p-8">
              <h3 className="text-lg font-bold">{title}</h3>
              <p className="mt-2 leading-relaxed text-gray-600">{body}</p>
            </div>
          ))}
        </div>
      </Band>
    </>
  )
}
